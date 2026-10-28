#!/usr/bin/env python3
"""Foreground, loopback-only launch with checkout-local state and runtime."""
import argparse
import json
import os
import runpy
import stat
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_BRANDING = runpy.run_path(str(ROOT / 'branding/runtime.py'))
LOCALE_BRANDING = runpy.run_path(str(ROOT / 'branding/runtime_locales.py'))


def _prepare_private_state(brand):
    root = ROOT.resolve()
    base = root / '.trial'
    paths = {'base': base, 'home': base / 'agent-home', 'state': base / 'state',
             'workspace': base / 'workspace', 'shared_auth': base / 'agent-home/shared',
             'codex_home': base / 'codex-home', 'claude_config': base / 'claude-config',
             'cron': base / 'agent-home/cron', 'sessions': base / 'agent-home/sessions',
             'logs': base / 'agent-home/logs', 'memories': base / 'agent-home/memories',
             'curator_logs': base / 'agent-home/logs/curator'}
    seeds = (paths['state'] / 'settings.json', paths['home'] / 'SOUL.md')
    # Check the complete owned boundary before mkdir, chmod, or file creation.
    # Reject internal aliases too: private state must not overwrite source files.
    for directory in paths.values():
        if directory.is_symlink() or directory.resolve() != directory or not directory.is_relative_to(root):
            raise RuntimeError('Isolated state paths must stay inside this checkout without symbolic links.')
        if directory.exists() and not directory.is_dir():
            raise RuntimeError('An isolated state directory path names an existing file.')
    for target in seeds:
        if target.is_symlink() or target.resolve() != target or (target.exists() and not target.is_file()):
            raise RuntimeError('An isolated state seed path is a symbolic link or an existing non-file.')
    required = (os.open, os.mkdir, os.stat)
    if (any(operation not in os.supports_dir_fd for operation in required)
            or not all(hasattr(os, name) for name in ('O_DIRECTORY', 'O_NOFOLLOW', 'fchmod'))):
        raise RuntimeError('This isolated launcher requires POSIX directory-relative, no-follow file operations.')

    # Managed runtime mode delegates permissions to this launcher. New files
    # inherit private modes; existing profile files are never chmodded.
    os.umask(0o077)
    descriptors = []
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW

    def open_directory(name, parent):
        try:
            os.mkdir(name, mode=0o700, dir_fd=parent)
        except FileExistsError:
            pass
        descriptor = os.open(name, flags, dir_fd=parent)
        descriptors.append(descriptor)
        return descriptor

    def seed(parent, filename, contents):
        try:
            descriptor = os.open(filename, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                 mode=0o600, dir_fd=parent)
        except FileExistsError:
            if not stat.S_ISREG(os.stat(filename, dir_fd=parent, follow_symlinks=False).st_mode):
                raise RuntimeError('An isolated state seed changed to a symbolic link or non-file.') from None
            return
        with os.fdopen(descriptor, 'w', encoding='utf-8') as output:
            output.write(contents)

    try:
        project_descriptor = os.open(root, flags)
        descriptors.append(project_descriptor)
        base_descriptor = open_directory('.trial', project_descriptor)
        # Only the owned root is tightened; it shields older shared-mode children.
        os.fchmod(base_descriptor, 0o700)
        handles = {Path('.'): base_descriptor}
        for directory in sorted(set(paths.values()) - {base}, key=lambda value: len(value.parts)):
            relative = directory.relative_to(base)
            handles[relative] = open_directory(relative.name, handles[relative.parent])
        seed(handles[Path('state')], 'settings.json', json.dumps({
            'show_claude_code_sessions': False, 'default_workspace': str(paths['workspace']),
        }))
        seed(handles[Path('agent-home')], 'SOUL.md', brand['assistant']['identity_instruction'].format(
            product=brand['product']['display_name'], publisher=brand['organization']['display_name'],
        ) + '\n')
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
    return paths


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8793)
    parser.add_argument('--agent-dir', type=Path)
    args = parser.parse_args(argv)
    agent = (args.agent_dir or ROOT / '.runtime/hermes-agent').resolve()
    if not (agent / 'run_agent.py').is_file():
        parser.error('Isolated agent source is missing. Run scripts/setup-altur.py first.')
    try:
        RUNTIME_BRANDING['verify_runtime_branding'](agent, project=ROOT)
        bundled_locales = LOCALE_BRANDING['verify_runtime_locales'](project=ROOT)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        parser.error(
            f'Private runtime branding could not be verified: {exc} '
            'Use this isolated interpreter to run scripts/setup-altur.py before starting.'
        )
    brand = json.loads((ROOT / 'branding/brand.json').read_text())
    try:
        paths = _prepare_private_state(brand)
    except (OSError, RuntimeError) as exc:
        parser.error(f'Cannot prepare private state: {exc} Review .trial paths before starting.')
    base, home, state = paths['base'], paths['home'], paths['state']
    # Drop inherited provider credentials, profile selectors, and CLI auth roots.
    # Retain host identity, executable discovery, and network certificate trust.
    network_ca = {'SSL_CERT_FILE', 'SSL_CERT_DIR', 'REQUESTS_CA_BUNDLE', 'CURL_CA_BUNDLE',
                  'NODE_EXTRA_CA_CERTS', 'AWS_CA_BUNDLE', 'HERMES_CA_BUNDLE'}
    credential_prefixes = ('HERMES_', 'OPENAI_', 'ANTHROPIC_', 'OPENROUTER_', 'AWS_',
                           'AZURE_', 'VERTEX_', 'GEMINI_')
    credential_suffixes = ('_KEY', '_TOKEN', '_SECRET', '_PASSWORD', '_PASSWD')
    credential_roots = {'GOOGLE_APPLICATION_CREDENTIALS', 'CODEX_HOME', 'CLAUDE_CONFIG_DIR'}
    env = {key: value for key, value in os.environ.items() if key in network_ca or not (
        key.startswith(credential_prefixes) or key.endswith(credential_suffixes) or key in credential_roots
    )}
    env.update(HERMES_HOME=str(home), HERMES_BASE_HOME=str(home), HERMES_CONFIG_PATH=str(home / 'config.yaml'),
               HERMES_WEBUI_STATE_DIR=str(state), HERMES_WEBUI_AGENT_DIR=str(agent), HERMES_WEBUI_PYTHON=sys.executable,
               HERMES_WEBUI_DEFAULT_WORKSPACE=str(base / 'workspace'), HERMES_WEBUI_HOST='127.0.0.1',
               HERMES_WEBUI_PORT=str(args.port), HERMES_BUNDLED_LOCALES=str(bundled_locales),
               HERMES_SHARED_AUTH_DIR=str(paths['shared_auth']), CODEX_HOME=str(paths['codex_home']),
               CLAUDE_CONFIG_DIR=str(paths['claude_config']),
               HERMES_MANAGED='altur-agent-webui',
               GATEWAY_RELAY_DISPLAY_NAME=brand['assistant']['display_name'],
               ALTUR_WEBUI_ISOLATED='1')
    os.chdir(ROOT)
    os.execve(sys.executable, [sys.executable, str(ROOT / 'server.py')], env)


if __name__ == '__main__':
    main()
