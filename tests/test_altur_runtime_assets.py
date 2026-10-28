"""Bundled manifest source edits never relabel authors or executable settings."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('altur_runtime_assets_test', ROOT/'branding/runtime.py')
runtime_branding = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime_branding)


def fixture(tmp_path, replacement='"@@PRODUCT@@ gateway adapter"'):
    project = tmp_path/'project'
    target = project/'.runtime/agent/plugins/platforms/email/plugin.yaml'
    target.parent.mkdir(parents=True)
    original = 'name: email-platform\ndescription: "Hermes gateway adapter"\nauthor: NousResearch\nrequires_env: [EMAIL_PASSWORD]\n'
    target.write_text(original)
    (project/'branding').mkdir()
    brand = {'product': {'display_name': 'Altur-Agent'}, 'organization': {'display_name': 'ArtemisProject'}, 'runtime': {'commit': 'pin'}}
    (project/'branding/brand.json').write_text(json.dumps(brand))
    path = 'plugins/platforms/email/plugin.yaml'
    digest = hashlib.sha256(original.encode()).hexdigest()
    registry = {'upstream_commit': 'pin', 'source_sha256': {path: digest}, 'files': [{
        'path': path, 'format': 'yaml', 'upstream_sha256': digest,
        'slots': [{'key_path': ['description'], 'upstream_literal': '"Hermes gateway adapter"', 'source_template': replacement}]}]}
    (project/'branding/runtime-literals.json').write_text(json.dumps(registry))
    return project, target, original


def test_manifest_changes_only_approved_display_leaf_and_restores(tmp_path):
    project, target, original = fixture(tmp_path)
    source = project/'.runtime/agent'
    runtime_branding.apply_runtime_branding(source, project=project)
    parsed = yaml.safe_load(target.read_text())
    assert parsed == {'name': 'email-platform', 'description': 'Altur-Agent gateway adapter', 'author': 'NousResearch', 'requires_env': ['EMAIL_PASSWORD']}
    runtime_branding.verify_runtime_branding(source, project=project)
    runtime_branding.restore_runtime_sources(source, project=project)
    assert target.read_text() == original


def test_manifest_rejects_unapproved_configuration_injection_without_writes(tmp_path):
    project, target, original = fixture(tmp_path, '"Altur gateway adapter"\nrequires_env: []\nignored: ')
    with pytest.raises(RuntimeError, match='unapproved|structured'):
        runtime_branding.apply_runtime_branding(project/'.runtime/agent', project=project)
    assert target.read_text() == original
    assert not (project/'.runtime/agent/.altur-branding.json').exists()


def test_manifest_rejects_edited_source(tmp_path):
    project, target, original = fixture(tmp_path)
    target.write_text(original.replace('EMAIL_PASSWORD', 'CUSTOM_PASSWORD'))
    with pytest.raises(RuntimeError, match='Unrecognized'):
        runtime_branding.apply_runtime_branding(project/'.runtime/agent', project=project)
    assert 'CUSTOM_PASSWORD' in target.read_text()
