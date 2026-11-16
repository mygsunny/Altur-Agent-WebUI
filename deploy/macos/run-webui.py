#!/usr/bin/env python3
"""Altru WebUI launcher for a Mac that already runs Hermes (portable copy of the
original evaluate-local.py from the .8 deployment).

Machine-specific values come from the environment (set them in the launchd plist):
  ALTRU_WEBUI_HOST   bind address (default 127.0.0.1; a LAN address requires persisted auth)
  ALTRU_WEBUI_PORT   port (default 8787)
  HERMES_HOME        Hermes home (default ~/.hermes)
  ALTRU_HERMES_PROFILE  optional named profile (~/.hermes/profiles/<name>); the
                     WebUI then shows only that profile's chats (isolated mode)
  ALTRU_WEBUI_DATA   WebUI state dir (default ~/.local/share/hermes-webui-evaluation)
No installer, updater or gateway restart is performed.
"""
import os
from pathlib import Path
import sys
import site
ROOT = Path(__file__).resolve().parents[2]
HOME = Path(os.environ.get('HERMES_HOME') or Path.home()/'.hermes')
DATA = Path(os.environ.get('ALTRU_WEBUI_DATA') or Path.home()/'.local/share/hermes-webui-evaluation')
HOST = os.environ.get('ALTRU_WEBUI_HOST', '127.0.0.1')
PROFILE = os.environ.get('ALTRU_HERMES_PROFILE', '').strip()
PORT = os.environ.get('ALTRU_WEBUI_PORT', '8787')
DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
# Deliberately override inherited profile/network/installer choices.
os.environ.update(HERMES_HOME=str(HOME), HERMES_WEBUI_AGENT_DIR=str(HOME/'hermes-agent'),
    HERMES_WEBUI_STATE_DIR=str(DATA), HERMES_WEBUI_HOST=HOST, HERMES_WEBUI_PORT=PORT,
    HERMES_WEBUI_AUTO_INSTALL='0', HERMES_DISABLE_LAZY_INSTALLS='1', HERMES_SKIP_CHMOD='1',
    HERMES_WEBUI_SKIP_ONBOARDING='1', PYTHONDONTWRITEBYTECODE='1')
if PROFILE:
    if PROFILE != Path(PROFILE).name or not (HOME/'profiles'/PROFILE).is_dir():
        raise SystemExit(f'Hermes profile not found: {HOME/"profiles"/PROFILE}')
    # Serve one named profile; the agent code stays in the base home.
    os.environ.update(HERMES_HOME=str(HOME/'profiles'/PROFILE), HERMES_BASE_HOME=str(HOME),
        HERMES_WEBUI_ISOLATED_PROFILE='1')
os.environ.pop('HERMES_RUNTIME_DIR', None)
os.environ.pop('HERMES_WEBUI_SETTINGS_FILE', None)
# Settings owns authentication. Never allow an inherited environment override.
os.environ.pop('HERMES_WEBUI_PASSWORD', None)
import runpy
_require_persisted_auth = runpy.run_path(str(Path(__file__).resolve().parent/'persisted-auth-guard.py'))['require_persisted_auth']
try:
    _persisted_hash = _require_persisted_auth(DATA)
except Exception:
    raise SystemExit('Refusing LAN bind: valid owner-only persisted authentication is required.') from None
sys.path.insert(0, str(HOME/'hermes-agent'))
# The installed managed runtime replaces site-packages during activation.
# Reactivate only this app's venv afterwards, without installing into Hermes.
import hermes_bootstrap
own_site = ROOT/'.venv/lib'/('python'+str(sys.version_info.major)+'.'+str(sys.version_info.minor))/'site-packages'
site.addsitedir(str(own_site))
sys.path.insert(0, str(own_site))
sys.path.insert(0, str(ROOT))
import server
from api.auth import get_password_hash, is_auth_enabled
if get_password_hash() != _persisted_hash or not is_auth_enabled():
    raise SystemExit('Refusing LAN bind: native authentication did not load persisted settings.')
# Must not consume/resume existing Gateway work automatically.
import api.background_process as bg
import api.gateway_delegation_wakeup as wake
import api.gateway_chat as chat
bg.start_drain_thread = lambda: False
bg.start_session_channel_reaper = lambda: False
server.auto_install_agent_deps = lambda **kwargs: None
server.fix_credential_permissions = lambda: None
wake.start_gateway_delegation_poller = lambda: None
chat.resume_gateway_runs_after_restart = lambda: None
# Refuse the UI's updater and gateway lifecycle controls (update via git pull instead).
_original_post = server.handle_post
_original_get = server.handle_get
def _safe_post(handler, parsed):
    if parsed.path.startswith('/api/updates/') or parsed.path in {'/api/gateway/start', '/api/gateway/stop', '/api/gateway/restart'}:
        from api.helpers import j
        j(handler, {'error': 'Disabled: existing Hermes and Gateway are preserved.'}, 403)
        return True
    return _original_post(handler, parsed)
def _safe_get(handler, parsed):
    if parsed.path == '/api/updates/check':
        from api.helpers import j
        j(handler, {'disabled': True})
        return True
    return _original_get(handler, parsed)
server.handle_post = _safe_post
server.handle_get = _safe_get
(DATA/'server.pid').write_text(str(os.getpid())+'\n')
print('[altru] Gateway completion draining, delegation wakeups and run resumption disabled.', flush=True)
server.main()
