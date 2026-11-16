"""Disposable loopback full HTTP handler; no startup workers or runtime installs.

Used by welcome-artwork.http.browser.cjs. All state lives in a TemporaryDirectory.
"""
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

with tempfile.TemporaryDirectory(prefix='welcome-http-') as home:
    os.environ['HERMES_HOME'] = home
    os.environ['HERMES_WEBUI_STATE_DIR'] = str(Path(home) / 'webui')
    os.environ['HERMES_WEBUI_TEST_NETWORK_BLOCK'] = '1'
    os.environ['HERMES_WEBUI_DISABLE_INTERNAL_AGENT_AUTOINSTALL'] = '1'
    os.environ.pop('HERMES_WEBUI_PASSWORD', None)
    from api.config import save_settings
    save_settings({'_set_password': os.environ['FIXTURE_PASSWORD'], 'theme': 'light', 'skin': 'ares', 'bot_name': 'Altru-Agent fixture'})
    from server import QuietHTTPServer, Handler
    from threading import Thread
    httpd = QuietHTTPServer(('127.0.0.1', 0), Handler)
    thread = Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    print(json.dumps({'url': 'http://127.0.0.1:%d' % httpd.server_port}), flush=True)
    try:
        sys.stdin.readline()
    finally:
        httpd.shutdown()
        httpd.server_close()
