"""Generate reviewed runtime locale defaults without needing a runtime checkout.

The registry contains complete pinned, parsed core catalogs and explicit owned
display-leaf templates. JSON documents named .yaml are valid runtime catalogs.
HERMES_BUNDLED_LOCALES selects these defaults below existing user/plugin layers.
No user locale, runtime source, conversation, or assembled message is rewritten.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import string
import tempfile


ROOT = Path(__file__).resolve().parents[1]
STAMP = '.altur-locales.json'


def _canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def _hash(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _directory(project: Path) -> Path:
    directory = project / 'branding/generated-locales'
    if (project / 'branding').is_symlink() or directory.is_symlink() or not directory.resolve().is_relative_to(project):
        raise RuntimeError('Generated locale defaults must stay inside this checkout.')
    return directory


def _target(directory: Path, filename: str) -> Path:
    target = directory / filename
    if target.is_symlink() or not target.resolve().is_relative_to(directory.resolve()):
        raise RuntimeError('Generated locale defaults must not overwrite symbolic links or external files.')
    return target


def _fields(value: str):
    try:
        return [(field, spec, conversion) for _, field, spec, conversion in string.Formatter().parse(value)
                if field is not None]
    except ValueError as exc:
        raise RuntimeError('A reviewed runtime locale template has invalid formatting fields.') from exc


def plan_runtime_locales(*, project: Path = ROOT) -> tuple[dict, dict[str, bytes]]:
    project = project.resolve()
    _directory(project)
    brand = json.loads((project / 'branding/brand.json').read_text())
    raw = (project / 'branding/runtime-locales.json').read_bytes()
    registry = json.loads(raw)
    if registry.get('upstream_commit') != brand['runtime']['commit']:
        raise RuntimeError('Runtime locale defaults do not match the pinned runtime revision.')
    values = {'@@PRODUCT@@': brand['product']['display_name'], '@@PUBLISHER@@': brand['organization']['display_name']}
    if any(not isinstance(value, str) or not value or '@@' in value or any(
            character in '{}\r\n' or ord(character) < 32 or ord(character) == 127 for character in value)
           for value in values.values()):
        raise RuntimeError('Runtime locale display names must not contain formatting braces or controls.')
    languages = registry['languages']
    if (not isinstance(languages, list) or not languages or 'en' not in languages
            or len(set(languages)) != len(languages)
            or any(not isinstance(lang, str) or not re.fullmatch(r'[a-z]{2,3}(?:-[a-z0-9]{2,8})*', lang)
                   for lang in languages)):
        raise RuntimeError('The runtime locale language inventory is invalid.')
    if set(languages) != set(registry['catalogs']) or set(registry['edits']) - set(languages):
        raise RuntimeError('The runtime locale catalog inventory is incomplete.')
    artifacts = {}
    for lang in languages:
        record = registry['catalogs'][lang]
        messages = record['messages']
        if not isinstance(messages, dict) or any(not isinstance(key, str) or not isinstance(value, str)
                                                 for key, value in messages.items()):
            raise RuntimeError(f'The pinned runtime locale catalog is invalid: {lang}')
        if _hash(_canonical(messages)) != record['baseline_sha256']:
            raise RuntimeError(f'The pinned runtime locale catalog checksum changed: {lang}')
        result = dict(messages)
        seen = set()
        for edit in registry['edits'].get(lang, []):
            key = edit['key']
            if key in seen or key not in messages:
                raise RuntimeError(f'Duplicate or missing runtime locale branding key: {lang}:{key}')
            seen.add(key)
            original = messages[key]
            if _hash(original.encode()) != edit['upstream_value_sha256']:
                raise RuntimeError(f'The reviewed runtime locale value changed: {lang}:{key}')
            template = edit['value_template']
            if not isinstance(template, str) or _fields(original) != _fields(template):
                raise RuntimeError(f'Runtime locale branding changes formatting fields: {lang}:{key}')
            if re.findall(r'`[^`]+`', original) != re.findall(r'`[^`]+`', template):
                raise RuntimeError(f'Runtime locale branding changes technical commands: {lang}:{key}')
            rendered = template
            for token, value in values.items():
                rendered = rendered.replace(token, value)
            if '@@' in rendered:
                raise RuntimeError(f'Unresolved runtime locale branding template: {lang}:{key}')
            result[key] = rendered
        artifacts[f'{lang}.yaml'] = (json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()
    stamp = {'schema_version': 1, 'upstream_commit': registry['upstream_commit'],
             'brand_sha256': _hash(_canonical(brand)), 'registry_sha256': _hash(raw),
             'files': {filename: _hash(data) for filename, data in artifacts.items()}}
    artifacts[STAMP] = (json.dumps(stamp, sort_keys=True, indent=2) + '\n').encode()
    return stamp, artifacts


def generate_runtime_locales(*, project: Path = ROOT) -> Path:
    project = project.resolve()
    _, artifacts = plan_runtime_locales(project=project)
    directory = _directory(project)
    # Validate every destination before writing any generated file.
    for filename in artifacts:
        _target(directory, filename)
    directory.mkdir(parents=True, exist_ok=True)
    for filename, data in artifacts.items():
        target = _target(directory, filename)
        if target.exists() and target.read_bytes() == data:
            continue
        descriptor, name = tempfile.mkstemp(prefix='.altur-locale-', dir=directory)
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, 'wb') as output:
                output.write(data)
            temporary.chmod(0o644)
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
    verify_runtime_locales(project=project)
    return directory


def verify_runtime_locales(*, project: Path = ROOT) -> Path:
    project = project.resolve()
    _, artifacts = plan_runtime_locales(project=project)
    directory = _directory(project)
    if not directory.is_dir() or {path.name for path in directory.glob('*.yaml')} != set(artifacts) - {STAMP}:
        raise RuntimeError('Runtime locale defaults are missing or outdated. Run scripts/generate-branding.py.')
    for filename, expected in artifacts.items():
        target = _target(directory, filename)
        if not target.is_file() or target.read_bytes() != expected:
            raise RuntimeError('Runtime locale defaults are missing or outdated. Run scripts/generate-branding.py.')
    return directory


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Generate or verify reviewed bundled runtime locale defaults.')
    parser.add_argument('--check', action='store_true')
    options = parser.parse_args()
    result = verify_runtime_locales() if options.check else generate_runtime_locales()
    print(f'Runtime locale defaults ready: {result}')
