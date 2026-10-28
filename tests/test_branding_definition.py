"""A single editable UI brand must win over stale defaults without erasing them."""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def settings(tmp_path, monkeypatch):
    from api import config
    from api.auth import _invalidate_password_hash_cache
    monkeypatch.setattr(config, 'SETTINGS_FILE', tmp_path / 'settings.json')
    monkeypatch.setitem(config.BRAND, 'ui', {'assistant_name_mode': 'brand'})
    _invalidate_password_hash_cache()
    yield config
    _invalidate_password_hash_cache()


def test_root_branding_file_has_primary_name_and_logo():
    b = json.loads((ROOT / 'BRANDING.json').read_text())
    assert b['name'] == 'Altur-Agent'
    assert (ROOT / b['logo']).is_file()


def test_managed_name_overrides_old_default_without_rewriting_file(settings):
    stored = {'bot_name': 'Hermes', 'theme': 'dark', 'unrelated': 'preserve'}
    settings.SETTINGS_FILE.write_text(json.dumps(stored))
    assert settings.load_settings()['bot_name'] == 'Altur-Agent'
    assert json.loads(settings.SETTINGS_FILE.read_text()) == stored


def test_other_settings_saves_preserve_the_saved_custom_name(settings):
    settings.SETTINGS_FILE.write_text(json.dumps({'bot_name': 'Captain Hermes'}))
    saved = settings.save_settings({'sound_enabled': True, 'bot_name': 'Altur-Agent'})
    assert saved['bot_name'] == 'Altur-Agent'
    assert json.loads(settings.SETTINGS_FILE.read_text())['bot_name'] == 'Captain Hermes'


def test_customizable_mode_retains_explicit_names(settings, monkeypatch):
    monkeypatch.setitem(settings.BRAND, 'ui', {'assistant_name_mode': 'customizable'})
    settings.SETTINGS_FILE.write_text(json.dumps({'bot_name': 'Hermes'}))
    assert settings.load_settings()['bot_name'] == 'Hermes'


def test_managed_name_rejects_competing_api_override(settings):
    from tests.test_auth_settings_safety import _post_settings
    result = _post_settings({'bot_name': 'Another Name'})
    assert result.status == 409
    assert 'BRANDING.json' in result.json_body()['error']


def test_frontend_managed_identity_preserves_profile_names():
    import re
    import shutil
    import subprocess
    node = shutil.which('node')
    if not node:
        pytest.skip('Node is required for the frontend identity check')
    source = (ROOT / 'static/ui.js').read_text()
    function = re.search(r'function assistantDisplayName\(\)\{.*?\n\}', source, re.S).group()
    script = "const assert=require('node:assert/strict'); const S={activeProfile:'default'}; const window={_botName:'Hermes',__ALTUR_BRAND__:{name:'Example Agent',assistant_name_mode:'brand'}};" + function + "assert.equal(assistantDisplayName(),'Example Agent'); S.activeProfile='research'; assert.equal(assistantDisplayName(),'Research'); S.activeProfile='default'; window.__ALTUR_BRAND__.assistant_name_mode='customizable'; assert.equal(assistantDisplayName(),'Hermes');"
    subprocess.run([node, '-e', script], check=True)
