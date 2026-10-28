"""Execute owned-message producers; do not filter model or customer content."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


def node(code):
    executable = shutil.which('node')
    if not executable:
        pytest.skip('Node.js is needed for frontend producer coverage')
    result = subprocess.run([executable, '-e', code], check=True, text=True, capture_output=True)
    return json.loads(result.stdout)


def test_actual_browser_export_handlers_use_brand_prefix():
    source = (ROOT / 'static/boot.js').read_text()
    handlers = source[source.index("$('btnDownload').onclick="):source.index("$('btnShareSession').onclick=")]
    html = source[source.index('function exportSessionHTML('):source.index("$('btnExportHTML').onclick=")]
    result = node("""
const elements={},downloads=[];
const S={session:{session_id:'example'}};
function $(id){return elements[id]||(elements[id]={});}
const document={baseURI:'http://localhost/subpath/',documentElement:{classList:{contains:()=>false}},createElement:()=>({click(){downloads.push(this.download)}})};
const location={href:'http://localhost/subpath/'};
const transcript=()=> 'User-authored Hermes and NousResearch must remain unchanged';
const getComputedStyle=()=>({getPropertyValue:()=>''});
""" + handlers + html + """
$('btnDownload').onclick(); $('btnExportJSON').onclick(); exportSessionHTML();
console.log(JSON.stringify(downloads));
""")
    assert result == ['altur-agent-example.md', 'altur-agent-example.json', 'altur-agent-example.html']


def test_manual_update_message_cannot_reinstall_upstream():
    source = (ROOT / 'static/ui.js').read_text()
    function = source[source.index('function _formatManualUpdateInstruction('):source.index('function _formatUpdateCheckError(')]
    result = node("const t=(key,value)=>value||key;" + function + "console.log(JSON.stringify(_formatManualUpdateInstruction({no_git:true,manual_update:true,behind:1})));" )
    assert 'nesquena' not in (result or '').lower()
    assert 'hermes-webui' not in (result or '').lower()


def test_theme_messages_render_labels_and_preserve_storage_ids():
    source = (ROOT / 'static/commands.js').read_text()
    function = source[source.index('async function cmdTheme('):source.index('// Subcommands owned by', source.index('async function cmdTheme('))]
    result = node("""
const _SKINS=[{name:'Default'},{name:'ArtemisProject',value:'nous'}],_LEGACY_THEME_MAP={};
const store={},messages=[]; const localStorage={getItem:k=>store[k]||'dark',setItem:(k,v)=>store[k]=v};
function _normalizeAppearance(t,s){return {theme:t,skin:s||'default'}}
function _applyTheme(){} function _applySkin(){} const api=async()=>({}); const $=()=>null;
const showToast=t=>messages.push(t); const t=k=>k+': ';
""" + function + """
(async()=>{await cmdTheme('nous');await cmdTheme('artemisproject');await cmdTheme('');console.log(JSON.stringify({messages,store}));})();
""")
    assert result['store']['hermes-skin'] == 'nous'
    assert all('nous' not in text.lower() for text in result['messages'])
    assert 'ArtemisProject' in result['messages'][0]


def test_onboarding_generated_note_is_provider_neutral():
    from api.onboarding import _UNSUPPORTED_PROVIDER_NOTE
    assert not any(word in _UNSUPPORTED_PROVIDER_NOTE.lower() for word in ('hermes', 'nous', 'nesquena'))


def test_new_profile_identity_uses_supported_soul_parameter(monkeypatch, tmp_path):
    import api.profiles as profiles
    import sys
    import types
    captured = []
    def create(name, *, soul=None, **kwargs):
        captured.append((soul, kwargs))
        path = tmp_path / 'profiles' / name
        path.mkdir(parents=True)
        (path / 'SOUL.md').write_text(soul or 'upstream default')
    stub = types.ModuleType('hermes_cli.profiles')
    stub.create_profile = create
    stub.seed_profile_skills = lambda *a, **k: None
    monkeypatch.setitem(sys.modules, 'hermes_cli.profiles', stub)
    monkeypatch.setattr(profiles, '_DEFAULT_HERMES_HOME', tmp_path)
    monkeypatch.setattr(profiles, '_is_isolated_profile_mode', lambda: False)
    monkeypatch.setattr(profiles, 'list_profiles_api', lambda: [])
    monkeypatch.setattr(profiles, '_validate_profile_model_selection', lambda *a: None)
    profiles.create_profile_api('fresh-brand')
    assert captured and ('You are ' + json.loads((ROOT/'BRANDING.json').read_text())['name']) in captured[0][0]


def test_help_moves_attribution_out_of_normal_product_guidance():
    html = (ROOT / 'static/altur-help.html').read_text()
    assert not any(word in html.lower() for word in ('hermes', 'nous', 'nesquena'))
    assert 'notices.html' in html


def test_unavailable_runtime_note_directs_to_supported_local_setup(monkeypatch, tmp_path):
    from api import onboarding
    monkeypatch.setattr(onboarding, '_HERMES_FOUND', False)
    monkeypatch.setattr(onboarding, '_get_active_hermes_home', lambda: tmp_path)
    status = onboarding._status_from_runtime({}, imports_ok=False)
    assert status['setup_state'] == 'agent_unavailable'
    assert 'local setup guide' in status['provider_note']
    assert 'bootstrap' not in status['provider_note'].lower()
