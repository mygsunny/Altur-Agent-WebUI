"""Executable native qualification; never enable unsafe writes from this probe."""
import json
from pathlib import Path
import platform
import shutil
import subprocess

import pytest


@pytest.mark.skipif(platform.system() != 'Darwin' or not shutil.which('swift'), reason='macOS Swift required')
def test_native_coordination_does_not_protect_against_noncooperative_atomic_save(tmp_path):
    result = subprocess.run(
        ['swift', str(Path(__file__).with_name('native_coordination_probe.swift')), str(tmp_path)],
        capture_output=True, text=True, timeout=90, check=True,
    )
    report = json.loads(result.stdout)
    assert report['coordinated_accessor_entered']
    assert report['external_process_completed_inside_accessor']
    assert report['baseline_backup_preserved']
    assert report['external_bytes_preserved'] is False
    assert report['qualification'] == 'unsafe-noncooperative-overwrite-demonstrated'
    proof = Path(report['proof_directory'])
    assert proof.parent == tmp_path
    assert (proof / 'baseline.backup').read_bytes() == b'synthetic-baseline'
    assert (proof / 'synthetic.bin').read_bytes() == b'synthetic-editor-save'
