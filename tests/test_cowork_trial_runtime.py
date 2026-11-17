"""Trial launcher import ordering and isolation (no inference mocks)."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_trial_bootstraps_selected_source_before_runtime(tmp_path):
    source = tmp_path / 'source'
    source.mkdir()
    (source / 'hermes_bootstrap.py').write_text("import os\nos.environ['TRIAL_BOOTSTRAPPED'] = 'yes'\n")
    (source / 'run_agent.py').write_text(
        "import os\n"
        "assert os.environ.get('TRIAL_BOOTSTRAPPED') == 'yes'\n"
        "assert 'OPENAI_API_KEY' not in os.environ\n"
        "assert os.environ['HERMES_HOME'].endswith('/trial/agent')\n"
        "assert os.environ['HOME'].endswith('/trial/home')\n"
    )
    trial = tmp_path / 'trial'
    result = subprocess.run([
        sys.executable, str(ROOT / 'tests/cowork_trial_server.py'),
        '--trial-dir', str(trial), '--agent-source', str(source), '--check-runtime',
    ], env={**os.environ, 'OPENAI_API_KEY': 'must-not-survive'}, text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'Runtime import OK' in result.stdout
    assert (trial / 'agent').is_dir()
    assert not (trial / 'url').exists()
