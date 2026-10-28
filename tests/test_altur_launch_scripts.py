"""Setup/start enforce the private runtime overlay before installation or launch."""
from __future__ import annotations

import ast
import asyncio
from contextlib import suppress
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import pytest


REPO = Path(__file__).resolve().parents[1]
SOURCE = 'IDENTITY = "You are Hermes Agent"\ndef identity():\n    return IDENTITY\n'


@pytest.fixture(autouse=True)
def restore_process_umask():
    """The real launcher keeps 077 across exec; direct unit calls must restore it."""
    previous = os.umask(0o077)
    os.umask(previous)
    try:
        yield
    finally:
        os.umask(previous)


def load_script(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), REPO / 'scripts' / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(runtime, *args):
    return subprocess.check_output(['git', '-C', str(runtime), *args], text=True).strip()


@pytest.fixture
def private_project(tmp_path):
    project = tmp_path / 'project'
    runtime = project / '.runtime/hermes-agent'
    runtime.mkdir(parents=True)
    (project / 'branding').mkdir()
    (runtime / 'run_agent.py').write_text(SOURCE)
    (runtime / 'unrelated.py').write_text('TECHNICAL_NAME = "hermes"\n')
    (runtime / 'pyproject.toml').write_text('[tool.uv]\noverride-dependencies = ["fixture-override==1"]\n')
    git(runtime, 'init', '--quiet')
    git(runtime, 'add', 'run_agent.py', 'unrelated.py', 'pyproject.toml')
    git(runtime, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
        '-c', 'commit.gpgsign=false', 'commit', '--quiet', '-m', 'Pinned fixture source')
    revision = git(runtime, 'rev-parse', 'HEAD')
    brand = {
        'product': {'display_name': 'Altur-Agent'},
        'organization': {'display_name': 'ArtemisProject'},
        'assistant': {'display_name': 'Altur-Agent', 'identity_instruction': 'You are {product}, published by {publisher}.'},
        'runtime': {'commit': revision, 'repository': str(runtime)},
    }
    (project / 'branding/brand.json').write_text(json.dumps(brand))
    registry = {'upstream_commit': revision, 'source_sha256': {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in runtime.glob('*.py')
    }, 'files': [{
        'path': 'run_agent.py', 'upstream_sha256': hashlib.sha256(SOURCE.encode()).hexdigest(),
        'slots': [{'upstream_literal': '"You are Hermes Agent"', 'source_template': '"You are @@PRODUCT@@"'}],
    }]}
    (project / 'branding/runtime-literals.json').write_text(json.dumps(registry))
    messages = {'explainer.persistence.default': 'Hermes could not save {home}.', 'provider.label': 'Nous Portal'}
    canonical = json.dumps(messages, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    locales = {'upstream_commit': revision, 'languages': ['en'], 'catalogs': {'en': {
        'messages': messages, 'baseline_sha256': hashlib.sha256(canonical).hexdigest(),
    }}, 'edits': {'en': [{
        'key': 'explainer.persistence.default',
        'upstream_value_sha256': hashlib.sha256(messages['explainer.persistence.default'].encode()).hexdigest(),
        'value_template': '@@PRODUCT@@ could not save {home}.',
    }]}}
    (project / 'branding/runtime-locales.json').write_text(json.dumps(locales))
    load_script('start-altur.py').LOCALE_BRANDING['generate_runtime_locales'](project=project)
    return project, runtime


def test_setup_restores_known_overlay_before_checkout_and_reapplies_before_install(private_project, monkeypatch):
    project, runtime = private_project
    setup = load_script('setup-altur.py')
    monkeypatch.setattr(setup, 'ROOT', project)
    monkeypatch.setattr(setup.sys, 'prefix', str(project / '.runtime/venv'))
    setup.RUNTIME_BRANDING['apply_runtime_branding'](runtime, project=project)
    brand_path = project / 'branding/brand.json'
    brand = json.loads(brand_path.read_text())
    brand['product']['display_name'] = 'Future Display'
    brand_path.write_text(json.dumps(brand))
    (runtime / 'operator-notes.txt').write_text('Preserve this untracked file.\n')
    commands = []

    def run(*args):
        commands.append(args)
        if args[0] == 'git':
            assert args[3:] == ('checkout', '--detach', brand['runtime']['commit'])
            assert (runtime / 'run_agent.py').read_text() == SOURCE
            assert not (runtime / setup.RUNTIME_BRANDING['STAMP']).exists()
            subprocess.run(args, check=True, cwd=project, capture_output=True)
        elif args[1:4] == ('-m', 'pip', 'install'):
            assert (runtime / 'run_agent.py').read_text() == SOURCE
        else:
            # Full runtime installation must observe already verified branding.
            setup.RUNTIME_BRANDING['verify_runtime_branding'](runtime, project=project)
            setup.LOCALE_BRANDING['verify_runtime_locales'](project=project)
            assert 'You are Future Display' in (runtime / 'run_agent.py').read_text()

    monkeypatch.setattr(setup, 'run', run)
    setup.main()
    assert len(commands) == 3
    assert commands[1] == (sys.executable, '-m', 'pip', 'install', 'uv==0.13.6', 'PyYAML>=6.0')
    assert '--overrides' in commands[2]
    assert (project / '.runtime/overrides.txt').read_text() == 'fixture-override==1\n'
    assert (runtime / 'unrelated.py').read_text() == 'TECHNICAL_NAME = "hermes"\n'
    assert (runtime / 'operator-notes.txt').read_text() == 'Preserve this untracked file.\n'


def test_fresh_setup_checks_out_pin_before_applying_overlay(private_project, monkeypatch, tmp_path):
    project, runtime = private_project
    origin = tmp_path / 'fixture-origin'
    runtime.rename(origin)
    (origin / 'unrelated.py').write_text('NEWER_REVISION = True\n')
    git(origin, 'add', 'unrelated.py')
    git(origin, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
        '-c', 'commit.gpgsign=false', 'commit', '--quiet', '-m', 'Newer default branch')
    brand_path = project / 'branding/brand.json'
    brand = json.loads(brand_path.read_text())
    brand['runtime']['repository'] = str(origin)
    brand_path.write_text(json.dumps(brand))
    setup = load_script('setup-altur.py')
    monkeypatch.setattr(setup, 'ROOT', project)
    monkeypatch.setattr(setup.sys, 'prefix', str(project / '.runtime/venv'))
    commands = []

    def run(*args):
        commands.append(args)
        if args[0] == 'git':
            subprocess.run(args, check=True, cwd=project, capture_output=True)
        elif args[1:4] != ('-m', 'pip', 'install'):
            assert git(runtime, 'rev-parse', 'HEAD') == brand['runtime']['commit']
            setup.RUNTIME_BRANDING['verify_runtime_branding'](runtime, project=project)

    monkeypatch.setattr(setup, 'run', run)
    setup.main()
    assert commands[0] == ('git', 'clone', str(origin), str(runtime))
    assert commands[1] == ('git', '-C', str(runtime), 'checkout', '--detach', brand['runtime']['commit'])
    assert 'You are Altur-Agent' in (runtime / 'run_agent.py').read_text()
    assert (runtime / 'unrelated.py').read_text() == 'TECHNICAL_NAME = "hermes"\n'


def test_setup_can_install_yaml_parser_privately_before_restoring_known_overlay(private_project, monkeypatch):
    project, runtime = private_project
    setup = load_script('setup-altur.py')
    monkeypatch.setattr(setup, 'ROOT', project)
    monkeypatch.setattr(setup.sys, 'prefix', str(project / '.runtime/venv'))
    setup.RUNTIME_BRANDING['apply_runtime_branding'](runtime, project=project)
    original_find_spec = setup.importlib.util.find_spec
    monkeypatch.setattr(setup.importlib.util, 'find_spec',
                        lambda name: None if name == 'yaml' else original_find_spec(name))
    commands = []

    def run(*args):
        commands.append(args)
        if args == (sys.executable, '-m', 'pip', 'install', 'PyYAML>=6.0'):
            assert 'You are Altur-Agent' in (runtime / 'run_agent.py').read_text()
            assert (runtime / setup.RUNTIME_BRANDING['STAMP']).is_file()
        elif args[0] == 'git':
            assert (runtime / 'run_agent.py').read_text() == SOURCE
            subprocess.run(args, check=True, cwd=project, capture_output=True)
        elif args[1:4] == ('-m', 'pip', 'install'):
            assert (runtime / 'run_agent.py').read_text() == SOURCE
        else:
            setup.RUNTIME_BRANDING['verify_runtime_branding'](runtime, project=project)
            setup.LOCALE_BRANDING['verify_runtime_locales'](project=project)

    monkeypatch.setattr(setup, 'run', run)
    setup.main()
    assert commands[0] == (sys.executable, '-m', 'pip', 'install', 'PyYAML>=6.0')
    assert commands[1][3:5] == ('checkout', '--detach')
    assert commands[2][-2:] == ('uv==0.13.6', 'PyYAML>=6.0')
    assert commands[3][1:4] == ('-m', 'uv', 'pip')


@pytest.mark.parametrize('stamped,tracked_file,staged', [
    (False, 'unrelated.py', False),
    (True, 'unrelated.py', False),
    (True, 'run_agent.py', False),
    (True, 'unrelated.py', True),
])
def test_setup_preserves_unrecognized_tracked_edits(private_project, monkeypatch, stamped, tracked_file, staged):
    project, runtime = private_project
    setup = load_script('setup-altur.py')
    monkeypatch.setattr(setup, 'ROOT', project)
    monkeypatch.setattr(setup.sys, 'prefix', str(project / '.runtime/venv'))
    if stamped:
        setup.RUNTIME_BRANDING['apply_runtime_branding'](runtime, project=project)
    changed = runtime / tracked_file
    changed.write_text(changed.read_text() + '\n# operator-owned change\n')
    if staged:
        git(runtime, 'add', tracked_file)
    before = {path: (runtime / path).read_bytes() for path in ('run_agent.py', 'unrelated.py')}
    head = git(runtime, 'rev-parse', 'HEAD')
    runner = Mock()
    monkeypatch.setattr(setup, 'run', runner)
    with pytest.raises(SystemExit, match='review|Review'):
        setup.main()
    runner.assert_not_called()
    assert git(runtime, 'rev-parse', 'HEAD') == head
    assert {path: (runtime / path).read_bytes() for path in before} == before


def test_setup_refuses_runtime_symlink_outside_checkout(private_project, monkeypatch, tmp_path):
    project, runtime = private_project
    external = tmp_path / 'external-runtime'
    runtime.parent.rename(external)
    (project / '.runtime').symlink_to(external, target_is_directory=True)
    setup = load_script('setup-altur.py')
    monkeypatch.setattr(setup, 'ROOT', project)
    monkeypatch.setattr(setup.sys, 'prefix', str(project / '.runtime/venv'))
    runner = Mock()
    monkeypatch.setattr(setup, 'run', runner)
    with pytest.raises(SystemExit, match='inside this checkout'):
        setup.main()
    runner.assert_not_called()
    assert (external / 'hermes-agent/run_agent.py').read_text() == SOURCE


@pytest.mark.parametrize('environment', ['global', 'repo-venv', 'private-base-interpreter'])
def test_setup_requires_private_virtualenv_before_any_subprocess(private_project, monkeypatch, environment):
    project, runtime = private_project
    setup = load_script('setup-altur.py')
    monkeypatch.setattr(setup, 'ROOT', project)
    if environment == 'global':
        monkeypatch.setattr(setup.sys, 'prefix', setup.sys.base_prefix)
    elif environment == 'repo-venv':
        monkeypatch.setattr(setup.sys, 'prefix', str(project / '.venv'))
    else:
        monkeypatch.setattr(setup.sys, 'prefix', str(project / '.runtime/python'))
        monkeypatch.setattr(setup.sys, 'base_prefix', setup.sys.prefix)
    run = Mock()
    probe = Mock()
    monkeypatch.setattr(setup.subprocess, 'run', run)
    monkeypatch.setattr(setup.subprocess, 'check_output', probe)
    with pytest.raises(SystemExit, match='dedicated virtual environment') as excinfo:
        setup.main()
    assert '.runtime/venv' in str(excinfo.value)
    assert 'scripts/setup-altur.py' in str(excinfo.value)
    run.assert_not_called()
    probe.assert_not_called()
    assert (runtime / 'run_agent.py').read_text() == SOURCE


@pytest.mark.parametrize('failure', ['unstamped', 'stale-brand', 'source-edit', 'unrelated-edit', 'wrong-revision', 'outside', 'missing-locales', 'stale-locales'])
def test_start_rejects_uncertified_runtime_before_state_or_launch(private_project, monkeypatch, capsys, failure):
    project, runtime = private_project
    start = load_script('start-altur.py')
    monkeypatch.setattr(start, 'ROOT', project)
    if failure != 'unstamped':
        start.RUNTIME_BRANDING['apply_runtime_branding'](runtime, project=project)
    if failure == 'stale-brand':
        path = project / 'branding/brand.json'
        brand = json.loads(path.read_text())
        brand['product']['display_name'] = 'Changed Display'
        path.write_text(json.dumps(brand))
    elif failure == 'source-edit':
        (runtime / 'run_agent.py').write_text(SOURCE + '\n# changed after certification\n')
    elif failure == 'unrelated-edit':
        (runtime / 'unrelated.py').write_text('# changed after certification\n')
    elif failure == 'wrong-revision':
        git(runtime, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
            '-c', 'commit.gpgsign=false', 'commit', '--quiet', '--allow-empty', '-m', 'Different revision')
    elif failure == 'outside':
        outside = project.parent / 'outside-runtime'
        runtime.rename(outside)
        runtime = outside
    elif failure == 'missing-locales':
        (project / 'branding/generated-locales/en.yaml').unlink()
    elif failure == 'stale-locales':
        (project / 'branding/generated-locales/en.yaml').write_text('{}\n')
    launch = Mock()
    monkeypatch.setattr(start.os, 'execve', launch)
    with pytest.raises(SystemExit) as excinfo:
        start.main(['--agent-dir', str(runtime)])
    assert excinfo.value.code == 2
    assert 'scripts/setup-altur.py' in capsys.readouterr().err
    assert not (project / '.trial').exists()
    launch.assert_not_called()


def test_start_preserves_flags_custom_identity_settings_and_isolated_environment(private_project, monkeypatch, tmp_path):
    project, runtime = private_project
    alternate = runtime.with_name('alternate-runtime')
    runtime.rename(alternate)
    start = load_script('start-altur.py')
    monkeypatch.setattr(start, 'ROOT', project)
    start.RUNTIME_BRANDING['apply_runtime_branding'](alternate, project=project)
    home = project / '.trial/agent-home'
    state = project / '.trial/state'
    home.mkdir(parents=True)
    state.mkdir()
    persona = 'My custom Hermes persona remains user-authored.\n'
    settings = '{"theme":"dark","default_workspace":"custom"}\n'
    (home / 'SOUL.md').write_text(persona)
    (state / 'settings.json').write_text(settings)
    # Local fixtures remain available for the runtime's own credential loading.
    local_env = 'OPENAI_API_KEY=fixture-local-key\nCUSTOM_TOKEN=fixture-local-token\n'
    (home / '.env').write_text(local_env)
    codex_home = project / '.trial/codex-home'
    claude_config = project / '.trial/claude-config'
    shared_auth = home / 'shared'
    for directory in (codex_home, claude_config, shared_auth):
        directory.mkdir()
        (directory / 'existing-fixture.json').write_text('{"fixture":"preserve"}\n')
    # Simulate an older shared-mode tree: protect only its owned outer root.
    base = project / '.trial'
    base.chmod(0o755)
    for directory in (home, state, codex_home, claude_config, shared_auth):
        directory.chmod(0o755)
    foreign = tmp_path / 'foreign-credentials'
    foreign.mkdir()
    foreign_auth = foreign / 'auth.json'
    foreign_auth.write_text('{"fixture":"never-read-or-modify"}\n')
    existing_files = [home / 'SOUL.md', state / 'settings.json', home / '.env', foreign_auth]
    existing_files.extend(directory / 'existing-fixture.json' for directory in (codex_home, claude_config, shared_auth))
    existing_modes = {path: stat.S_IMODE(path.stat().st_mode) for path in existing_files}
    monkeypatch.setenv('HERMES_HOME', '/fixture/foreign-home')
    monkeypatch.setenv('HERMES_PROFILE', 'foreign-profile')
    credential_env = {
        'OPENAI_API_KEY': 'fixture-inherited-key',
        'CUSTOM_API_KEY': 'fixture-inherited-key',
        'AWS_ACCESS_KEY_ID': 'fixture-inherited-key',
        'AWS_SECRET_ACCESS_KEY': 'fixture-inherited-secret',
        'AWS_PROFILE': 'fixture-foreign-profile',
        'AWS_SHARED_CREDENTIALS_FILE': str(foreign_auth),
        'AZURE_CLIENT_SECRET': 'fixture-inherited-secret',
        'AZURE_CONFIG_DIR': str(foreign),
        'FAL_KEY': 'foreign-fal-key',
        'CUSTOM_PROVIDER_PASSWORD': 'foreign-provider-password',
        'GOOGLE_APPLICATION_CREDENTIALS': str(foreign_auth),
        'VERTEX_CREDENTIALS_PATH': str(foreign_auth),
        'GEMINI_CLI_OAUTH_CREDS_PATH': str(foreign_auth),
        'CUSTOM_ACCESS_TOKEN': 'fixture-inherited-token',
        'CUSTOM_TOKEN': 'fixture-inherited-token',
        'CUSTOM_SECRET': 'fixture-inherited-secret',
        'CUSTOM_PRIVATE_KEY': 'fixture-inherited-private-key',
        'CLAUDE_CODE_OAUTH_TOKEN': 'fixture-inherited-token',
    }
    for key, value in credential_env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv('CODEX_HOME', str(foreign))
    monkeypatch.setenv('CLAUDE_CONFIG_DIR', str(foreign))
    monkeypatch.setenv('HERMES_SHARED_AUTH_DIR', str(foreign))
    retained_env = {
        'HOME': str(tmp_path / 'host-home'), 'PATH': '/fixture/bin:/usr/bin',
        'SSL_CERT_FILE': '/fixture/ca.pem', 'SSL_CERT_DIR': '/fixture/certs',
        'REQUESTS_CA_BUNDLE': '/fixture/ca.pem', 'CURL_CA_BUNDLE': '/fixture/ca.pem',
        'NODE_EXTRA_CA_CERTS': '/fixture/ca.pem', 'AWS_CA_BUNDLE': '/fixture/ca.pem',
        'HERMES_CA_BUNDLE': '/fixture/ca.pem',
    }
    for key, value in retained_env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv('KEEP_FIXTURE_VALUE', 'keep')
    monkeypatch.setattr(start.os, 'chdir', lambda path: None)
    launch = Mock(side_effect=SystemExit(0))
    monkeypatch.setattr(start.os, 'execve', launch)
    with pytest.raises(SystemExit) as excinfo:
        start.main(['--port', '9876', '--agent-dir', str(alternate)])
    assert excinfo.value.code == 0
    python, argv, env = launch.call_args.args
    assert python == sys.executable
    assert argv == [sys.executable, str(project / 'server.py')]
    assert env['HERMES_WEBUI_AGENT_DIR'] == str(alternate.resolve())
    assert env['HERMES_WEBUI_HOST'] == '127.0.0.1'
    assert env['HERMES_WEBUI_PORT'] == '9876'
    assert env['HERMES_HOME'] == env['HERMES_BASE_HOME'] == str(home)
    assert env['HERMES_CONFIG_PATH'] == str(home / 'config.yaml')
    assert env['HERMES_WEBUI_STATE_DIR'] == str(state)
    assert env['HERMES_WEBUI_DEFAULT_WORKSPACE'] == str(project / '.trial/workspace')
    assert env['ALTUR_WEBUI_ISOLATED'] == '1'
    assert env['HERMES_BUNDLED_LOCALES'] == str(project / 'branding/generated-locales')
    assert env['HERMES_MANAGED'] == 'altur-agent-webui'
    assert env['GATEWAY_RELAY_DISPLAY_NAME'] == 'Altur-Agent'
    assert env['HERMES_SHARED_AUTH_DIR'] == str(shared_auth)
    assert env['CODEX_HOME'] == str(codex_home)
    assert env['CLAUDE_CONFIG_DIR'] == str(claude_config)
    for key, value in retained_env.items():
        assert env[key] == value
    assert env['KEEP_FIXTURE_VALUE'] == 'keep'
    assert not ({'HERMES_PROFILE'} | credential_env.keys()) & env.keys()
    assert (home / 'SOUL.md').read_text() == persona
    assert (home / '.env').read_text() == local_env
    assert (state / 'settings.json').read_text() == settings
    for directory in (codex_home, claude_config, shared_auth):
        assert (directory / 'existing-fixture.json').read_text() == '{"fixture":"preserve"}\n'
    assert foreign_auth.read_text() == '{"fixture":"never-read-or-modify"}\n'
    assert stat.S_IMODE(base.stat().st_mode) == 0o700
    for directory in (home, state, codex_home, claude_config, shared_auth):
        assert stat.S_IMODE(directory.stat().st_mode) == 0o755
    for path, mode in existing_modes.items():
        assert stat.S_IMODE(path.stat().st_mode) == mode


def test_start_seeds_only_new_instance_identity_and_workspace_defaults(private_project, monkeypatch):
    project, runtime = private_project
    start = load_script('start-altur.py')
    monkeypatch.setattr(start, 'ROOT', project)
    start.RUNTIME_BRANDING['apply_runtime_branding'](runtime, project=project)
    monkeypatch.setattr(start.os, 'chdir', lambda path: None)

    def check_private_exec(*args):
        mask = os.umask(0o077)
        os.umask(mask)
        assert mask == 0o077
        raise SystemExit(0)

    monkeypatch.setattr(start.os, 'execve', check_private_exec)
    with pytest.raises(SystemExit):
        start.main([])
    home = project / '.trial/agent-home'
    state = project / '.trial/state'
    assert (home / 'SOUL.md').read_text() == 'You are Altur-Agent, published by ArtemisProject.\n'
    assert json.loads((state / 'settings.json').read_text()) == {
        'show_claude_code_sessions': False,
        'default_workspace': str(project / '.trial/workspace'),
    }
    assert (home / 'shared').is_dir()
    assert (project / '.trial/codex-home').is_dir()
    assert (project / '.trial/claude-config').is_dir()
    for directory in (project / '.trial', home, state, home / 'shared', project / '.trial/codex-home', project / '.trial/claude-config'):
        assert stat.S_IMODE(directory.stat().st_mode) == 0o700
    for relative in ('cron', 'sessions', 'logs', 'memories', 'logs/curator'):
        assert stat.S_IMODE((home / relative).stat().st_mode) == 0o700
    for path in (home / 'SOUL.md', state / 'settings.json'):
        assert stat.S_IMODE(path.stat().st_mode) == 0o600


@pytest.mark.parametrize('escape', [
    'trial', 'agent-home', 'state', 'workspace', 'codex-home', 'claude-config', 'agent-home/shared',
    'agent-home/cron', 'agent-home/sessions', 'agent-home/logs', 'agent-home/memories', 'agent-home/logs/curator',
    'seed-soul', 'seed-settings', 'file-instead-of-state',
])
def test_start_refuses_escaped_or_aliased_state_before_any_write(private_project, monkeypatch, tmp_path, capsys, escape):
    project, runtime = private_project
    start = load_script('start-altur.py')
    monkeypatch.setattr(start, 'ROOT', project)
    start.RUNTIME_BRANDING['apply_runtime_branding'](runtime, project=project)
    outside = tmp_path / 'external-state'
    outside.mkdir()
    outside.chmod(0o755)
    external_file = outside / 'existing.json'
    external_file.write_text('{"fixture":"preserve external bytes"}\n')
    base = project / '.trial'
    if escape == 'trial':
        base.symlink_to(outside, target_is_directory=True)
    elif escape == 'seed-soul':
        (base / 'agent-home').mkdir(parents=True)
        (base / 'agent-home/SOUL.md').symlink_to(external_file)
    elif escape == 'seed-settings':
        (base / 'state').mkdir(parents=True)
        (base / 'state/settings.json').symlink_to(external_file)
    elif escape == 'file-instead-of-state':
        base.mkdir()
        (base / 'state').write_text('Preserve this unexpected existing file.\n')
    else:
        target = base / escape
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(outside, target_is_directory=True)
    before_tree = sorted(str(path.relative_to(base)) for path in base.rglob('*'))
    before_root_mode = stat.S_IMODE(base.lstat().st_mode)
    before_mask = os.umask(0o077)
    os.umask(before_mask)
    launch = Mock()
    monkeypatch.setattr(start.os, 'execve', launch)
    with pytest.raises(SystemExit) as excinfo:
        start.main([])
    assert excinfo.value.code == 2
    assert 'private state' in capsys.readouterr().err
    launch.assert_not_called()
    assert sorted(str(path.relative_to(base)) for path in base.rglob('*')) == before_tree
    assert stat.S_IMODE(base.lstat().st_mode) == before_root_mode
    assert stat.S_IMODE(outside.stat().st_mode) == 0o755
    assert external_file.read_text() == '{"fixture":"preserve external bytes"}\n'
    assert list(outside.iterdir()) == [external_file]
    after_mask = os.umask(0o077)
    os.umask(after_mask)
    assert after_mask == before_mask


@pytest.mark.parametrize('replacement', ['trial-directory', 'settings-seed'])
def test_start_no_follow_operations_stop_symlink_swap_after_preflight(private_project, monkeypatch, tmp_path, replacement):
    project, runtime = private_project
    start = load_script('start-altur.py')
    monkeypatch.setattr(start, 'ROOT', project)
    start.RUNTIME_BRANDING['apply_runtime_branding'](runtime, project=project)
    outside = tmp_path / 'external-state'
    outside.mkdir()
    outside.chmod(0o755)
    external = outside / 'existing.json'
    external.write_text('{"fixture":"never overwrite"}\n')
    original_open = os.open
    replaced = False

    def swap_before_open(path, flags, *args, **kwargs):
        nonlocal replaced
        if not replaced and replacement == 'trial-directory' and path == '.trial' and kwargs.get('dir_fd') is not None:
            (project / '.trial').rmdir()
            (project / '.trial').symlink_to(outside, target_is_directory=True)
            replaced = True
        elif not replaced and replacement == 'settings-seed' and path == 'settings.json' and flags & os.O_CREAT:
            (project / '.trial/state/settings.json').symlink_to(external)
            replaced = True
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(start.os, 'open', swap_before_open)
    monkeypatch.setattr(start.os, 'supports_dir_fd', os.supports_dir_fd | {swap_before_open})
    launch = Mock()
    monkeypatch.setattr(start.os, 'execve', launch)
    with pytest.raises(SystemExit) as excinfo:
        start.main([])
    assert excinfo.value.code == 2
    assert replaced
    launch.assert_not_called()
    assert stat.S_IMODE(outside.stat().st_mode) == 0o755
    assert external.read_text() == '{"fixture":"never overwrite"}\n'
    assert list(outside.iterdir()) == [external]


def test_fresh_private_state_satisfies_pinned_managed_home_initialization(private_project, monkeypatch):
    """Exercise the runtime initializer and identity seeder without starting an agent."""
    project, _ = private_project
    source = REPO / '.runtime/hermes-agent'
    if not (source / 'hermes_cli/config_home.py').is_file():
        pytest.skip('Private pinned runtime source is needed for managed home initialization')
    brand_pin = json.loads((REPO / 'branding/brand.json').read_text())['runtime']['commit']
    assert git(source, 'rev-parse', 'HEAD') == brand_pin
    start = load_script('start-altur.py')
    monkeypatch.setattr(start, 'ROOT', project)
    brand = json.loads((project / 'branding/brand.json').read_text())
    paths = start._prepare_private_state(brand)
    soul = paths['home'] / 'SOUL.md'
    before = soul.read_bytes()
    monkeypatch.setenv('HERMES_MANAGED', 'altur-agent-webui')

    def source_module(name, path):
        # Execute the actual source without writing __pycache__ into the runtime.
        module = ModuleType(name)
        module.__file__ = str(path)
        exec(compile(path.read_text(), str(path), 'exec'), module.__dict__)
        return module

    soul_module = source_module('fixture_default_soul', source / 'hermes_cli/default_soul.py')
    config_source = ast.parse((source / 'hermes_cli/config.py').read_text())
    seed = next(node for node in config_source.body if isinstance(node, ast.FunctionDef)
                and node.name == '_ensure_default_soul_md')
    unexpected_chmod = Mock(side_effect=AssertionError('Managed initialization altered existing permissions'))
    namespace = {'Path': Path, 'os': os, 'tempfile': tempfile, 'suppress': suppress,
                 'is_legacy_template_soul': soul_module.is_legacy_template_soul,
                 'DEFAULT_SOUL_MD': soul_module.DEFAULT_SOUL_MD, '_secure_file': unexpected_chmod}
    exec(compile(ast.Module(body=[seed], type_ignores=[]), 'runtime-default-soul-seeder', 'exec'), namespace)
    config_stub = ModuleType('hermes_cli.config')
    config_stub.is_managed = lambda: os.environ.get('HERMES_MANAGED') == 'altur-agent-webui'
    config_stub._ensure_default_soul_md = namespace['_ensure_default_soul_md']
    config_stub._secure_dir = unexpected_chmod
    monkeypatch.setitem(sys.modules, 'hermes_cli.config', config_stub)
    acl = source_module('hermes_dir_acl', source / 'hermes_dir_acl.py')
    monkeypatch.setitem(sys.modules, 'hermes_dir_acl', acl)
    initializer = source_module('fixture_config_home', source / 'hermes_cli/config_home.py')
    ensured = set()
    # Managed initialization ignores the non-managed optional skeleton and
    # requires its four core directories to have been provisioned already.
    initializer.initialize_home(paths['home'], ('not-needed-in-managed-mode',), ensured)
    for relative in ('cron', 'sessions', 'logs', 'memories', 'logs/curator'):
        assert (paths['home'] / relative).is_dir()
        assert stat.S_IMODE((paths['home'] / relative).stat().st_mode) == 0o700
    assert not (paths['home'] / 'not-needed-in-managed-mode').exists()
    assert str(paths['home']) in ensured
    assert soul.read_bytes() == before
    unexpected_chmod.assert_not_called()
    mask = os.umask(0o077)
    os.umask(mask)
    assert mask == 0o077


def test_start_exports_process_scoped_managed_policy_and_manifest_relay_name(private_project, monkeypatch):
    project, runtime = private_project
    brand_path = project / 'branding/brand.json'
    brand = json.loads(brand_path.read_text())
    brand['assistant']['display_name'] = 'Scoped Assistant Display'
    brand_path.write_text(json.dumps(brand))
    start = load_script('start-altur.py')
    monkeypatch.setattr(start, 'ROOT', project)
    start.RUNTIME_BRANDING['apply_runtime_branding'](runtime, project=project)
    start.LOCALE_BRANDING['generate_runtime_locales'](project=project)
    monkeypatch.setenv('HERMES_MANAGED', 'false')
    monkeypatch.setenv('GATEWAY_RELAY_DISPLAY_NAME', 'Inherited external identity')
    monkeypatch.setattr(start.os, 'chdir', lambda path: None)
    launch = Mock(side_effect=SystemExit(0))
    monkeypatch.setattr(start.os, 'execve', launch)
    with pytest.raises(SystemExit):
        start.main([])
    env = launch.call_args.args[2]
    assert env['HERMES_MANAGED'] == 'altur-agent-webui'
    assert env['GATEWAY_RELAY_DISPLAY_NAME'] == 'Scoped Assistant Display'
    assert os.environ['HERMES_MANAGED'] == 'false'
    assert os.environ['GATEWAY_RELAY_DISPLAY_NAME'] == 'Inherited external identity'
    assert not list((project / '.trial').rglob('.managed'))


def test_pinned_runtime_managed_guard_refuses_channel_update_before_spawn(tmp_path, monkeypatch):
    """Execute actual pinned getter/config/async-handler definitions in isolation."""
    runtime = REPO / '.runtime/hermes-agent'
    if not (runtime / 'hermes_constants.py').is_file():
        pytest.skip('Private pinned runtime source is needed for the managed-update boundary check')
    brand = json.loads((REPO / 'branding/brand.json').read_text())
    assert git(runtime, 'rev-parse', 'HEAD') == brand['runtime']['commit']
    constants = ast.parse((runtime / 'hermes_constants.py').read_text())
    config = ast.parse((runtime / 'hermes_cli/config.py').read_text())
    slash = ast.parse((runtime / 'gateway/slash_commands.py').read_text())
    constants_to_keep = {'_MANAGED_TRUE_VALUES', '_LEGACY_MANAGED_SYSTEM', '_IGNORED_MANAGED_VALUES', '_MANAGED_FALSE_VALUES'}
    declarations = [node for node in constants.body if (
        isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id in constants_to_keep
                                           for target in node.targets)
    ) or isinstance(node, ast.FunctionDef) and node.name == 'get_managed_system']
    declarations.extend(node for node in config.body if isinstance(node, ast.FunctionDef)
                        and node.name in {'is_managed', 'format_managed_message'})
    handler = next(node for node in ast.walk(slash) if isinstance(node, ast.AsyncFunctionDef)
                   and node.name == '_handle_update_command')
    home = tmp_path / 'managed-home'
    home.mkdir()
    forbidden = Mock(side_effect=AssertionError('Managed update reached process or executable resolution'))
    namespace = {'Path': Path, 'os': os, 'get_hermes_home': lambda: home,
                 'MessageEvent': object, '_spawn_detached_update': forbidden,
                 't': lambda key: 'update this installation'}
    exec(compile(ast.Module(body=declarations + [handler], type_ignores=[]), 'managed-runtime-boundary', 'exec'), namespace)
    monkeypatch.setenv('HERMES_MANAGED', 'altur-agent-webui')
    assert namespace['get_managed_system']() == 'altur-agent-webui'
    assert namespace['is_managed']()
    config_stub = ModuleType('hermes_cli.config')
    config_stub.is_managed = namespace['is_managed']
    config_stub.format_managed_message = namespace['format_managed_message']
    run_stub = ModuleType('gateway.run')
    run_stub._hermes_home = home
    run_stub._resolve_hermes_bin = forbidden
    monkeypatch.setitem(sys.modules, 'hermes_cli.config', config_stub)
    monkeypatch.setitem(sys.modules, 'gateway.run', run_stub)
    owner = SimpleNamespace(_UPDATE_ALLOWED_PLATFORMS={'fixture-channel'}, _schedule_update_notification_watch=forbidden)
    event = SimpleNamespace(source=SimpleNamespace(platform='fixture-channel'))
    response = asyncio.run(namespace['_handle_update_command'](owner, event))
    assert 'altur-agent-webui' in response
    assert 'managed' in response.lower()
    assert 'setup' in response.lower()
    forbidden.assert_not_called()
    assert list(home.iterdir()) == []
