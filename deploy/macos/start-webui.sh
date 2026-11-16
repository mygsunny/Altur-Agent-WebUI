#!/bin/sh
# launchd entry point. Repo root is two levels up from this script.
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
exec env -u PYTHONPATH -u HERMES_WEBUI_PASSWORD "$ROOT/.venv/bin/python" -I -c "import runpy,sys; runpy.run_path(sys.argv[1],run_name='__main__')" "$ROOT/deploy/macos/run-webui.py"
