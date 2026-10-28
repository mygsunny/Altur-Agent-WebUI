"""Distribution identity and isolation at the fork's packaging boundaries.

These checks parse build declarations and exercise the real MCP declarations;
they do not build a container, activate an auto-start task, or use live data.
"""

from __future__ import annotations

import ast
import copy
import json
import shlex
from pathlib import Path

import pytest
import yaml


REPO = Path(__file__).resolve().parents[1]
BRAND = json.loads((REPO / "branding/brand.json").read_text(encoding="utf-8"))
MULTI_CONTAINER_FILES = (
    "docker-compose.two-container.yml",
    "docker-compose.three-container.yml",
)
MCP_TOOL_NAMES = {
    "list_projects",
    "create_project",
    "rename_project",
    "delete_project",
    "rename_session",
    "move_session",
    "list_sessions",
}


@pytest.mark.parametrize("filename", MULTI_CONTAINER_FILES)
def test_compose_builds_webui_from_fork_without_relabeling_runtime(filename):
    services = yaml.safe_load((REPO / filename).read_text(encoding="utf-8"))["services"]
    webui = services["hermes-webui"]
    # `image` alone used to pull the unbranded upstream WebUI. Rebuilding this
    # checkout must stay the default even when a same-named image is cached.
    assert webui["build"] == {"context": ".", "dockerfile": "Dockerfile"}
    assert webui["image"] == "altur-agent-webui:local"
    assert webui["pull_policy"] == "build"
    assert services["hermes-agent"]["image"] == "nousresearch/hermes-agent:latest"
    # Service/storage identifiers are compatibility boundaries, not branding.
    assert webui["container_name"] == "hermes-webui"
    assert "hermes-home:/home/hermeswebui/.hermes" in webui["volumes"]
    assert "hermes-agent-src:/home/hermeswebui/.hermes/hermes-agent:ro" in webui["volumes"]


def test_docker_metadata_uses_manifest_product_and_publisher():
    labels = {}
    for line in (REPO / "Dockerfile").read_text(encoding="utf-8").splitlines():
        if not line.lstrip().upper().startswith("LABEL "):
            continue
        for field in shlex.split(line, comments=True)[1:]:
            key, value = field.split("=", 1)
            labels[key] = value
    assert labels["maintainer"] == BRAND["organization"]["display_name"]
    assert BRAND["product"]["display_name"] in labels["description"]


def test_docker_context_excludes_checkout_local_runtime_and_customer_data():
    rules = {
        line.strip().strip("/")
        for line in (REPO / ".dockerignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    # Dockerfile copies the filtered checkout into /apptoo. These roots can
    # contain credentials, model dependencies, sessions, or uploaded files.
    for root in (
        ".runtime", ".trial", ".venv", "work", "outputs", "data", "attachments",
    ):
        assert root in rules, f"Docker context must exclude local {root}/"
        assert f"!{root}" not in rules
    assert ".env*" in rules
    assert ".webui_password" in rules


def _mcp_declarations():
    """Execute only advertised declarations, without importing config/profile IO."""
    module = ast.parse((REPO / "mcp_server.py").read_text(encoding="utf-8"))
    declarations = [
        node for node in module.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id in {"server", "TOOLS"}
                for target in node.targets)
    ]
    assert len(declarations) == 2
    return module, compile(ast.Module(body=declarations, type_ignores=[]), "mcp_server.py", "exec")


@pytest.mark.parametrize("product_name", [BRAND["product"]["display_name"], "Future Product Display"])
def test_mcp_advertises_manifest_identity_and_preserves_protocol_tool_names(product_name):
    pytest.importorskip("mcp")
    from mcp.server import Server
    from mcp.types import Tool

    module, declarations = _mcp_declarations()
    assert any(
        isinstance(node, ast.ImportFrom) and node.module == "api.branding"
        and any(alias.name == "BRAND" for alias in node.names)
        for node in module.body
    )
    brand = copy.deepcopy(BRAND)
    brand["product"]["display_name"] = product_name
    namespace = {"BRAND": brand, "Server": Server, "Tool": Tool}
    exec(declarations, namespace)

    # This is the SDK's initialization payload seen by an MCP client.
    assert namespace["server"].create_initialization_options().server_name == product_name
    assert {tool.name for tool in namespace["TOOLS"]} == MCP_TOOL_NAMES
    assert len(namespace["TOOLS"]) == len(MCP_TOOL_NAMES)
    handlers = next(
        node.value for node in module.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "HANDLERS" for target in node.targets)
    )
    assert isinstance(handlers, ast.Dict)
    assert {ast.literal_eval(key) for key in handlers.keys} == MCP_TOOL_NAMES
