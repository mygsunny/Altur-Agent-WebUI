"""Assistant names belong to server state; product branding is a fallback."""
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
NAME = json.loads((ROOT / 'BRANDING.json').read_text())['name']

@pytest.fixture
def settings(tmp_path, monkeypatch):
    from api import config
    from api.auth import _invalidate_password_hash_cache
    monkeypatch.setattr(config, 'SETTINGS_FILE', tmp_path / 'settings.json')
    _invalidate_password_hash_cache()
    yield config
    _invalidate_password_hash_cache()


def test_root_branding_file_has_primary_name_and_logo():
    b = json.loads((ROOT / 'BRANDING.json').read_text())
    assert b['name'] == NAME
    assert (ROOT / b['logo']).is_file()


@pytest.mark.parametrize('name', ['Tom', 'Hermes', 'Captain Hermes'])
def test_configured_names_win_without_rewriting_file(settings, name):
    stored = {'bot_name': name, 'theme': 'dark', 'unrelated': 'preserve'}
    settings.SETTINGS_FILE.write_text(json.dumps(stored))
    assert settings.load_settings()['bot_name'] == name
    assert json.loads(settings.SETTINGS_FILE.read_text()) == stored
    saved = settings.save_settings({'sound_enabled': True})
    assert saved['bot_name'] == name
    assert json.loads(settings.SETTINGS_FILE.read_text())['bot_name'] == name


@pytest.mark.parametrize('stored', [{}, {'bot_name': None}, {'bot_name': ''}, {'bot_name': '   '}])
def test_only_missing_names_fall_back(settings, stored):
    settings.SETTINGS_FILE.write_text(json.dumps(stored))
    assert settings.load_settings()['bot_name'] == NAME
    assert json.loads(settings.SETTINGS_FILE.read_text()) == stored


def test_api_name_change_is_persisted_at_source(settings):
    from tests.test_auth_settings_safety import _post_settings
    result = _post_settings({'bot_name': 'Tom'})
    assert result.status == 200
    assert result.json_body()['bot_name'] == 'Tom'
    assert settings.load_settings()['bot_name'] == 'Tom'
    assert json.loads(settings.SETTINGS_FILE.read_text())['bot_name'] == 'Tom'


def test_identity_instruction_uses_server_name_and_honors_persona(settings):
    from api.streaming import _webui_ephemeral_system_prompt
    settings.SETTINGS_FILE.write_text(json.dumps({'bot_name': 'Tom'}))
    prompt = _webui_ephemeral_system_prompt(None)
    assert 'configured assistant name for this WebUI instance is Tom' in prompt
    assert 'introduce yourself as Tom' in prompt
    assert f'You are {NAME}' not in prompt
    profile_prompt = _webui_ephemeral_system_prompt(None, {'profile': 'research'})
    assert 'introduce yourself as Research' in profile_prompt
    assert 'introduce yourself as Tom' not in profile_prompt
    persona = 'I am Captain Hermes; quote NousResearch exactly.'
    prompt = _webui_ephemeral_system_prompt(persona)
    assert persona in prompt and 'introduce yourself as Tom' not in prompt


def test_frontend_uses_server_name_and_falls_back_only_when_empty():
    import re
    import shutil
    import subprocess
    node = shutil.which('node')
    if not node:
        pytest.skip('Node is required for the frontend identity check')
    source = (ROOT / 'static/ui.js').read_text()
    function = re.search(r'function assistantDisplayName\(\)\{.*?\n\}', source, re.S).group()
    script = "const assert=require('node:assert/strict'); const S={activeProfile:'default'}; const window={_botName:'Tom',__ALTUR_BRAND__:{name:'Example Agent',assistant_name_mode:'brand'}};" + function + "assert.equal(assistantDisplayName(),'Tom'); window._botName='Hermes'; assert.equal(assistantDisplayName(),'Hermes'); for(const value of ['',null,'   ']){window._botName=value;assert.equal(assistantDisplayName(),'Example Agent');} S.activeProfile='research'; assert.equal(assistantDisplayName(),'Research');"
    subprocess.run([node, '-e', script], check=True)
