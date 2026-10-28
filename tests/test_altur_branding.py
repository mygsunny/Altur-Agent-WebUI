"""Brand contract: owned assets/prompts change, compatibility/user data do not."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_manifest_and_original_artwork():
 b=json.loads((ROOT/'branding/brand.json').read_text())
 assert b['product']['display_name']=='Altur-Agent'
 assert b['organization']['display_name']=='ArtemisProject'
 assert hashlib.sha256((ROOT/b['assets']['source']).read_bytes()).hexdigest()=='2a5d0b99454f3ca9b160e4879a1f9a518e1f22374360af1d25021da7f11cafde'
 assert b['distribution']['support'] is None

def test_icon_family_and_pwa_relative_scope():
 from PIL import Image
 for size in (16,32,192,512):
  assert Image.open(ROOT/f'static/favicon-{size}.png').size==(size,size)
 m=json.loads((ROOT/'static/manifest.json').read_text())
 assert m['name']=='Altur-Agent' and m['scope']=='./' and m['id']=='./'
 assert all(not i['src'].startswith('/') for i in m['icons'])
 assert '630.5 961.9' not in (ROOT/'static/index.html').read_text()
 assert '630.5 961.9' not in (ROOT/'static/share.html').read_text()

def test_ephemeral_identity_preserves_persona_and_payload():
 from api.streaming import _webui_ephemeral_system_prompt
 p=_webui_ephemeral_system_prompt(None)
 assert 'You are Altur-Agent' in p
 custom='I am Captain Hermes; quote NousResearch exactly.'
 p=_webui_ephemeral_system_prompt(custom)
 assert custom in p and 'You are Altur-Agent' not in p

def test_compatibility_and_first_paint():
 s=(ROOT/'static/index.html').read_text()
 assert '<title>Altur-Agent</title>' in s
 assert 'X-Hermes-CSRF-Token' in s and "'hermes-theme'" in s
 assert 'alt="Altur-Agent logo"' in s
 assert 'hermes-shell-' in (ROOT/'static/sw.js').read_text()
 assert '/^(hermes-shell-|altur-shell-)/' in (ROOT/'static/sw.js').read_text()

def test_isolated_home_does_not_fall_back(monkeypatch,tmp_path):
 from api.paths import _platform_default_hermes_home
 monkeypatch.setenv('ALTUR_WEBUI_ISOLATED','1');monkeypatch.setenv('HERMES_BASE_HOME',str(tmp_path))
 assert _platform_default_hermes_home()==tmp_path

def test_updater_refuses_mutation(monkeypatch):
 from api import updates
 monkeypatch.setattr(updates,'_run_git',lambda *a,**k: (_ for _ in ()).throw(AssertionError('must not invoke Git')))
 assert updates._apply_update_inner('webui')['ok'] is False
 assert updates._apply_update_inner('agent')['ok'] is False

def test_generator_is_repeatable_and_renames_only_owned_sources(tmp_path):
 import shutil
 import pytest
 pytest.importorskip('resvg_py')
 catalog=json.loads((ROOT/'branding/literals.json').read_text())
 files=set(catalog)|{'BRANDING.json','branding/brand.json','branding/literals.json','branding/assets/source/portrait-icon.svg','static/manifest.json','static/sw.js','scripts/generate-branding.py'}
 for f in files:
  dest=tmp_path/f;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/f,dest)
 def run():subprocess.run([sys.executable,str(tmp_path/'scripts/generate-branding.py')],check=True)
 run();first={f:hashlib.sha256((tmp_path/f).read_bytes()).hexdigest() for f in files};run()
 assert first=={f:hashlib.sha256((tmp_path/f).read_bytes()).hexdigest() for f in files}
 p=tmp_path/'BRANDING.json';b=json.loads(p.read_text());b['name']='Example Agent';b['logo']='branding/assets/source/new.svg';(tmp_path/b['logo']).write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 50"><rect width="100" height="50" fill="red"/></svg>');p.write_text(json.dumps(b));run()
 assert json.loads((tmp_path/'branding/brand.json').read_text())['assets']['view_box']==[0,0,100,50]
 assert 'window.__ALTUR_BRAND__' in (tmp_path/'static/branding.js').read_text()
 assert 'fill="red"' in (tmp_path/'static/brand-logo.svg').read_text()
 s=(tmp_path/'static/index.html').read_text()
 assert '<title>Example Agent</title>' in s
 assert 'X-Hermes-CSRF-Token' in s and "'hermes-theme'" in s
 assert 'Example Agent' in (tmp_path/'static/i18n.js').read_text()

def test_historical_generic_titles_still_recognized():
 from api.models import _sidebar_title_is_generic_webui
 assert _sidebar_title_is_generic_webui('Hermes WebUI')
 assert _sidebar_title_is_generic_webui('Hermes WebUI #12')
 assert _sidebar_title_is_generic_webui('Altur-Agent')
 assert not _sidebar_title_is_generic_webui('My factual discussion about Hermes')

def test_branding_cannot_change_passkey_identifiers():
 s=(ROOT/'api/passkeys.py').read_text()
 assert 'hashlib.sha256(rp_id.encode()).digest()[:16]' in s
 assert '"displayName": "Altur-Agent"' in s

def test_export_footer_uses_product():
 from api.session_export_html import render_session_html
 html=render_session_html({'messages':[{'role':'user','content':'Discuss Hermes and NousResearch factually.'}]})
 assert 'Exported from Altur-Agent on' in html
 assert 'Discuss Hermes and NousResearch factually.' in html
