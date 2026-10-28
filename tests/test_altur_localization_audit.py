"""Execute the real locale and frontend display producers with neutral fixtures.

This tests application-owned text, not a ban on upstream words in customer
content, legal attribution, real providers or compatibility identifiers.
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
BRAND = json.loads((ROOT / 'branding/brand.json').read_text())
SUPPORTED = {'en', 'it', 'ja', 'ru', 'es', 'de', 'zh', 'zh-Hant', 'pt', 'ko', 'fr', 'cs', 'tr', 'pl', 'vi'}
OWNED_UPSTREAM = re.compile(r'\bh[eèé]rm|nesquena|nousresearch|(?<![A-Za-z])(?:nous|naus)(?![A-Za-z])', re.I)


def node_json(program):
    executable = os.environ.get('ALTUR_TEST_NODE') or shutil.which('node')
    if not executable:
        pytest.skip('Node.js is required for executable locale audit; set ALTUR_TEST_NODE or PATH')
    result = subprocess.run([executable], input=program, check=True, capture_output=True, text=True, timeout=30)
    return json.loads(result.stdout)


def locale_program(check):
    """Load the real module, including loadLocale(), in an isolated Node VM."""
    return """
const vm=require('node:vm');
const sandbox={localStorage:{getItem:()=>null,setItem(){}},navigator:{languages:['en'],language:'en'},document:{documentElement:{}}};
vm.createContext(sandbox);
const source=""" + json.dumps((ROOT / 'static/i18n.js').read_text()) + ";\nconst check=" + json.dumps(check) + ";\nconsole.log(vm.runInContext(source+'\\n'+check,sandbox,{timeout:10000}));"


@pytest.fixture(scope='module')
def locale_audit():
    return node_json(locale_program("""
JSON.stringify((()=>{
 const allKeys=[...new Set(Object.values(LOCALES).flatMap(bundle=>Object.keys(bundle)))];
 const values=[];
 for(const locale of Object.keys(LOCALES)){
  setLocale(locale);
  for(const key of allKeys){
   const value=t(key,11,'AUDIT_PROVIDER',1);
   if(typeof value==='string')values.push({locale,key,value,fallback:LOCALES[locale][key]===undefined});
  }
 }
 return {codes:Object.keys(LOCALES),values};
})())
"""))


def test_all_supported_locale_values_and_real_fallback_are_brand_neutral(locale_audit):
    assert set(locale_audit['codes']) == SUPPORTED
    assert any(row['fallback'] for row in locale_audit['values']), 'The real English fallback path must be exercised'
    failures = [row for row in locale_audit['values'] if OWNED_UPSTREAM.search(row['value'])]
    assert not failures, failures


def test_real_locale_alias_and_fallback_return_current_copy():
    result = node_json(locale_program("""
JSON.stringify((()=>{
 setLocale('zh-TW'); const alias=resolveLocale('zh-TW'),chinese=t('cmd_theme');
 const old=LOCALES.it.cmd_theme;delete LOCALES.it.cmd_theme;
 setLocale('it');const fallback=t('cmd_theme');LOCALES.it.cmd_theme=old;
 return {alias,chinese,fallback,english:LOCALES.en.cmd_theme};
})())
"""))
    assert result['alias'] == 'zh-Hant'
    assert result['fallback'] == result['english']
    assert not OWNED_UPSTREAM.search(result['fallback'])
    assert not OWNED_UPSTREAM.search(result['chinese'])


def test_localized_interpolation_preserves_customer_and_provider_names():
    result = node_json(locale_program("""
JSON.stringify(Object.keys(LOCALES).map(locale=>{
 setLocale(locale);
 return {locale,text:t('provider_mismatch_warning','Customer Hermes model','NousResearch provider chosen by customer')};
}))
"""))
    for row in result:
        assert 'Customer Hermes model' in row['text'], row
        assert 'NousResearch provider chosen by customer' in row['text'], row


def test_real_theme_command_displays_labels_but_keeps_legacy_skin_key():
    boot = (ROOT / 'static/boot.js').read_text()
    source = (ROOT / 'static/commands.js').read_text()
    skins = boot[boot.index('const _SKINS='):boot.index('];', boot.index('const _SKINS=')) + 2]
    start = source.index('async function cmdTheme(')
    command = source[start:source.index('// Subcommands owned by', start)]
    result = node_json("""
const store={},messages=[],_LEGACY_THEME_MAP={};
const localStorage={getItem:k=>store[k]||null,setItem:(k,v)=>store[k]=v};
const _normalizeAppearance=(theme,skin)=>({theme:theme||'dark',skin:skin||'default'});
function _applyTheme(){}function _applySkin(){}const api=async()=>({});const $=()=>null;
const showToast=text=>messages.push(text),t=key=>key+': ';
""" + skins + command + """
(async()=>{
 await cmdTheme('nous');
 await cmdTheme(""" + json.dumps(BRAND['organization']['display_name']) + """);
 await cmdTheme('');await cmdTheme('invalid');
 console.log(JSON.stringify({store,messages}));
})();
""")
    assert result['store']['hermes-skin'] == 'nous'
    assert all(not OWNED_UPSTREAM.search(message) for message in result['messages'])
    assert BRAND['organization']['display_name'] in result['messages'][0]
    assert BRAND['organization']['display_name'] in result['messages'][1]


def test_real_browser_export_handlers_use_application_owned_prefix():
    source = (ROOT / 'static/boot.js').read_text()
    handlers = source[source.index("$('btnDownload').onclick="):source.index("$('btnShareSession').onclick=")]
    html = source[source.index('function exportSessionHTML('):source.index("$('btnExportHTML').onclick=")]
    result = node_json("""
const controls={},downloads=[];const S={session:{session_id:'audit-session'}};
const $=id=>controls[id]||(controls[id]={});
const document={baseURI:'http://localhost/subpath/',documentElement:{classList:{contains:()=>false}},createElement:()=>({click(){downloads.push(this.download)}})};
const location={href:'http://localhost/subpath/'};
const transcript=()=> 'Keep customer-authored Hermes and NousResearch references.';
const getComputedStyle=()=>({getPropertyValue:()=>''});
""" + handlers + html + """
$('btnDownload').onclick();$('btnExportJSON').onclick();exportSessionHTML();
console.log(JSON.stringify(downloads));
""")
    prefix = BRAND['distribution']['export_prefix']
    assert result == [f'{prefix}-audit-session.{extension}' for extension in ('md', 'json', 'html')]


def test_actual_docker_update_fallback_has_no_upstream_distribution():
    source = (ROOT / 'static/ui.js').read_text()
    start = source.index('function _formatManualUpdateInstruction(')
    function = source[start:source.index('function _formatUpdateCheckError(', start)]
    result = node_json(locale_program(function + """
JSON.stringify((()=>{
 setLocale('en');
 return {manual:_formatManualUpdateInstruction({no_git:true,manual_update:true,behind:2}),idle:_formatManualUpdateInstruction({})};
})())
"""))
    assert result['idle'] is None
    assert result['manual']
    assert not OWNED_UPSTREAM.search(result['manual'])
    assert 'ghcr.io/' not in result['manual']


def test_onboarding_uses_supported_setup_and_single_product_label():
    result = node_json(locale_program("""
JSON.stringify(Object.keys(LOCALES).map(locale=>{
 setLocale(locale);
 return {locale,unavailable:t('onboarding_notice_system_unavailable'),label:t('onboarding_check_agent')};
}))
"""))
    name = BRAND['product']['display_name']
    for row in result:
        assert name in row['unavailable'], row
        assert 'bootstrap' not in row['unavailable'].lower(), row
        assert name + ' Agent' not in row['label'], row
