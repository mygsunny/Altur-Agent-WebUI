#!/usr/bin/env python3
"""Install a pinned runtime only within this checkout. Never invoke global bootstrap."""
import json
import importlib.util
import runpy
import subprocess
import sys
from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_BRANDING = runpy.run_path(str(ROOT / 'branding/runtime.py'))
LOCALE_BRANDING = runpy.run_path(str(ROOT / 'branding/runtime_locales.py'))


def run(*args):
    subprocess.run(args, check=True, cwd=ROOT)


def _brand_runtime(action, destination):
    try:
        RUNTIME_BRANDING[action](destination, project=ROOT)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        raise SystemExit(
            f'Cannot prepare the private runtime safely: {exc} '
            'Review the private source and branding inputs, then rerun scripts/setup-altur.py.'
        ) from exc


def main():
    destination = ROOT / '.runtime/hermes-agent'
    private = (ROOT / '.runtime').resolve()
    if not private.is_relative_to(ROOT.resolve()) or not destination.resolve().is_relative_to(private):
        raise SystemExit('The private runtime path must stay inside this checkout; review .runtime before setup.')
    environment = Path(sys.prefix).resolve()
    if environment == Path(sys.base_prefix).resolve() or not environment.is_relative_to(private):
        raise SystemExit(
            'Setup requires a dedicated virtual environment inside this checkout\'s .runtime directory. '
            'Create .runtime/venv with Python 3.14 and run scripts/setup-altur.py using that environment\'s Python.'
        )
    brand = json.loads((ROOT / 'branding/brand.json').read_text())
    destination.parent.mkdir(exist_ok=True)
    if not destination.exists():
        run('git', 'clone', brand['runtime']['repository'], str(destination))
    else:
        # Generated overlays are never staged. Preserve any operator-owned
        # index changes before the helper considers restoring known sources.
        staged = subprocess.check_output(
            ['git', '-C', str(destination), 'diff', '--cached', '--name-only'], text=True,
        )
        if staged.strip():
            raise SystemExit('The private runtime has staged source edits; review them before rerunning scripts/setup-altur.py.')
        if (destination / RUNTIME_BRANDING['STAMP']).exists():
            # Restoring a reviewed YAML asset overlay needs only this parser,
            # installed into the already verified private environment.
            if importlib.util.find_spec('yaml') is None:
                run(sys.executable, '-m', 'pip', 'install', 'PyYAML>=6.0')
            _brand_runtime('restore_runtime_sources', destination)
        tracked = subprocess.check_output(
            ['git', '-C', str(destination), 'status', '--porcelain', '--untracked-files=no'], text=True,
        )
        if tracked.strip():
            raise SystemExit('The private runtime has local source edits; refusing checkout. Review them before rerunning scripts/setup-altur.py.')
    run('git', '-C', str(destination), 'checkout', '--detach', brand['runtime']['commit'])
    # Small packaging tools precede overlay validation; no Agent is imported.
    run(sys.executable, '-m', 'pip', 'install', 'uv==0.13.6', 'PyYAML>=6.0')
    _brand_runtime('apply_runtime_branding', destination)
    LOCALE_BRANDING['generate_runtime_locales'](project=ROOT)
    # Use the runtime's declared overrides, matching the upstream Docker installer.
    project = tomllib.loads((destination / 'pyproject.toml').read_text())
    overrides = ROOT / '.runtime/overrides.txt'
    overrides.write_text('\n'.join(project.get('tool', {}).get('uv', {}).get('override-dependencies', [])) + '\n')
    run(sys.executable, '-m', 'uv', 'pip', 'install', '--python', sys.executable,
        '--overrides', str(overrides), '-e', str(destination), '-r', str(ROOT / 'requirements.txt'))
    print('Runtime installed and branding verified. Start with this interpreter and scripts/start-altur.py.')


if __name__ == '__main__':
    main()
