"""Disposable real-Handler co-work trial; no startup/background consumers.

Run from the checkout with its test venv. All credentials and state stay in the
ignored .cowork-local directory. Optional --agent-source adds an existing Agent
source checkout; it does not copy credentials or configure inference services.
"""
import argparse
import os
from pathlib import Path
import secrets
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--agent-source', type=Path)
    parser.add_argument('--trial-dir', type=Path, help='Independent disposable trial state directory')
    parser.add_argument('--check-runtime', action='store_true', help='Import selected runtime and exit without a server')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    base = (args.trial_dir or root / '.cowork-local').resolve()
    for name in ('home', 'state', 'workspace', 'agent', 'tmp'):
        (base / name).mkdir(parents=True, exist_ok=True, mode=0o700)
    password_file = base / 'password'
    if not password_file.exists():
        password_file.write_text(secrets.token_urlsafe(32))
        password_file.chmod(0o600)
    env = {
        'PATH': os.environ['PATH'], 'HOME': str(base / 'home'),
        'TMPDIR': str(base / 'tmp'), 'HERMES_HOME': str(base / 'agent'),
        'HERMES_BASE_HOME': str(base / 'agent'),
        'HERMES_CONFIG_PATH': str(base / 'agent/config.yaml'),
        'HERMES_WEBUI_STATE_DIR': str(base / 'state'),
        'HERMES_WEBUI_DEFAULT_WORKSPACE': str(base / 'workspace'),
        'HERMES_WEBUI_HOST': '127.0.0.1', 'HERMES_WEBUI_SKIP_ONBOARDING': '1',
        'HERMES_WEBUI_PASSWORD': password_file.read_text(),
        'HERMES_WEBUI_COOKIE_NAME': 'cowork_trial_session',
        'HERMES_DISABLE_LAZY_INSTALLS': '1',
    }
    if args.agent_source:
        source = args.agent_source.resolve(strict=True)
        if not (source / 'run_agent.py').is_file():
            parser.error('--agent-source must contain run_agent.py')
        env['HERMES_WEBUI_AGENT_DIR'] = str(source)
    os.environ.clear()
    os.environ.update(env)
    sys.path.insert(0, str(root))
    # Same early activation as the normal launcher: bootstrap must run before
    # WebUI imports YAML or caches any profile-sensitive Agent modules.
    if args.agent_source:
        from managed_agent_startup import activate_managed_agent
        activate_managed_agent()
    if args.check_runtime:
        if not args.agent_source:
            parser.error('--check-runtime requires --agent-source')
        __import__('run_agent')
        print('Runtime import OK', flush=True)
        return
    from server import Handler, QuietHTTPServer
    httpd = QuietHTTPServer(('127.0.0.1', 0), Handler)
    url = f'http://127.0.0.1:{httpd.server_address[1]}'
    (base / 'url').write_text(url)
    print('Isolated co-work trial: ' + url, flush=True)
    print('No gateway watcher, run resumption, plugin loading or background consumers started.', flush=True)
    httpd.serve_forever()


if __name__ == '__main__':
    main()
