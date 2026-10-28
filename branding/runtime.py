"""Apply reviewed display-copy patches to this fork's private, pinned runtime.

This is a source packaging operation, never a filter on prompts, tool output,
provider responses, logs, history, credentials, or customer files.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import runpy
from pathlib import Path
import stat
import string
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
_ASSETS = runpy.run_path(str(Path(__file__).with_name('runtime_assets.py')))
STAMP = '.altur-branding.json'
# Extension installations and customer workspaces are deliberately outside this
# executable-source boundary. Expected hashes still verify every declared file.
CORE_SOURCE_ROOTS = frozenset({
    'agent', 'tools', 'gateway', 'hermes_cli', 'providers', 'hermes_platform',
    'cron', 'acp_adapter', 'tui_gateway', 'pm',
})
GENERATED_DIRS = frozenset({
    '.git', '.venv', 'venv', '__pycache__', 'build', 'dist', 'node_modules',
    '.pytest_cache', '.mypy_cache', '.ruff_cache',
})


def _hash(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


class _DisplayStructure(ast.NodeTransformer):
    def visit_FormattedValue(self, node):
        # Expressions, nested f-strings and format specifications are executable
        # input. Even their string constants must remain exactly unchanged.
        return node

    def visit_Constant(self, node):
        if isinstance(node.value, str):
            node.value = '<display-string>'
        return node


def _structure(source: str, *, expression: bool = False) -> str:
    try:
        tree = ast.parse('(\n' + source + '\n)', mode='eval') if expression else ast.parse(source)
    except (SyntaxError, ValueError) as exc:
        raise RuntimeError('Runtime patch changes executable structure or is invalid Python.') from exc
    return ast.dump(_DisplayStructure().visit(tree), include_attributes=False)


def _validate_slot(original: str, replacement: str, relative: str) -> None:
    try:
        before = ast.parse('(\n' + original + '\n)', mode='eval').body
        after = ast.parse('(\n' + replacement + '\n)', mode='eval').body
    except (SyntaxError, ValueError) as exc:
        raise RuntimeError(f'Runtime patch changes executable structure: {relative}') from exc
    if not isinstance(before, (ast.Constant, ast.JoinedStr)) or (
        isinstance(before, ast.Constant) and not isinstance(before.value, str)
    ) or _structure(original, expression=True) != _structure(replacement, expression=True):
        raise RuntimeError(f'Runtime patch changes executable structure: {relative}')
    if isinstance(before, ast.Constant) and isinstance(after, ast.Constant):
        # Plain .format()-style templates also carry argument contracts. A
        # literal JSON/code example may not be a format string at all.
        try:
            fields = [(field, spec, conversion) for _, field, spec, conversion
                      in string.Formatter().parse(before.value) if field is not None]
        except ValueError:
            return
        try:
            new_fields = [(field, spec, conversion) for _, field, spec, conversion
                          in string.Formatter().parse(after.value) if field is not None]
        except ValueError as exc:
            raise RuntimeError(f'Runtime patch changes executable structure: {relative}') from exc
        if fields != new_fields:
            raise RuntimeError(f'Runtime patch changes executable structure: {relative}')


def _literal_spans(source: str) -> dict[str, list[tuple[int, int]]]:
    """Find whole string expressions, excluding strings inside f-string code."""
    tree = ast.parse(source)
    parents = {id(child): node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    lines = source.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))

    def offset(line: int, byte_column: int) -> int:
        return offsets[line - 1] + len(lines[line - 1].encode()[:byte_column].decode())

    result = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Constant, ast.JoinedStr)):
            continue
        if isinstance(node, ast.Constant) and not isinstance(node.value, str):
            continue
        if isinstance(parents.get(id(node)), ast.JoinedStr):
            continue
        ancestor = node
        while id(ancestor) in parents:
            ancestor = parents[id(ancestor)]
            if isinstance(ancestor, ast.FormattedValue):
                break
        else:
            start = offset(node.lineno, node.col_offset)
            end = offset(node.end_lineno, node.end_col_offset)
            result.setdefault(source[start:end], []).append((start, end))
    return result


def _python_slot_span(source: str, spans: list[tuple[int, int]], slot: dict,
                      relative: str) -> tuple[int, int]:
    """Select the reviewed AST occurrence, never other identical literals."""
    has_line, has_column = 'line' in slot, 'column' in slot
    if not has_line and not has_column:
        if len(spans) != 1:
            raise RuntimeError(f'Ambiguous runtime branding slot in {relative}; line and byte column are required.')
        return spans[0]
    line, column = slot.get('line'), slot.get('column')
    if (not has_line or not has_column or type(line) is not int or type(column) is not int
            or line < 1 or column < 0):
        raise RuntimeError(f'Runtime branding slot requires valid line and byte column coordinates: {relative}')
    selected = []
    for start, end in spans:
        actual_line = source.count('\n', 0, start) + 1
        line_start = source.rfind('\n', 0, start) + 1
        actual_column = len(source[line_start:start].encode('utf-8'))
        if (actual_line, actual_column) == (line, column):
            selected.append((start, end))
    if len(selected) != 1:
        raise RuntimeError(f'Runtime branding slot does not match the exact line and byte column: {relative}')
    return selected[0]


def _pristine_source(record: dict, current: bytes, previous: dict) -> str:
    relative = record['path']
    if _hash(current) == record['upstream_sha256']:
        return current.decode('utf-8')
    if _hash(current) != previous.get('files', {}).get(relative):
        raise RuntimeError(f'Unrecognized runtime edits in {relative}; refusing to overwrite them.')
    source = current.decode('utf-8')
    regions = previous.get('regions', {}).get(relative, [])
    cursor = 0
    for region in regions:
        start, end = region['start'], region['end']
        if not isinstance(start, int) or not isinstance(end, int) or not cursor <= start <= end <= len(source):
            raise RuntimeError(f'Cannot verify original runtime source: {relative}')
        cursor = end
    for region in reversed(regions):
        source = source[:region['start']] + region['original'] + source[region['end']:]
    if _hash(source.encode()) != record['upstream_sha256']:
        raise RuntimeError(f'Cannot verify original runtime source: {relative}')
    return source


def _assert_private(path: Path, project: Path) -> None:
    private = (project / '.runtime').resolve()
    if private.is_relative_to(project.resolve()) and path.is_relative_to(private):
        return
    # Only this application's staged Docker copy qualifies for the fixed path.
    if (project.resolve() == Path('/app') and Path('/.within_container').is_file()
            and path == Path('/app/hermes-agent-src')):
        return
    raise RuntimeError('Runtime branding is restricted to this checkout’s private runtime copy.')


def _checked_target(runtime: Path, relative: str) -> Path:
    name = Path(relative)
    if not relative or name.is_absolute() or '..' in name.parts or name == Path('.'):
        raise RuntimeError('Runtime branding slot must be a relative path that never escapes the private source tree.')
    target = runtime / name
    if target.is_symlink() or target.resolve() != target:
        raise RuntimeError('Runtime branding does not follow source or stamp symlinks.')
    if not target.is_relative_to(runtime):
        raise RuntimeError('Runtime branding slot escapes the private source tree.')
    if target.exists() and not stat.S_ISREG(target.stat().st_mode):
        raise RuntimeError('Runtime branding requires regular source and stamp files.')
    return target


def _core_source_paths(runtime: Path) -> set[str]:
    paths = {p.name for p in runtime.glob('*.py')}
    for name in CORE_SOURCE_ROOTS:
        directory = runtime / name
        if directory.is_symlink():
            raise RuntimeError('Unexpected runtime source symlink in a core package.')
        if not directory.exists():
            continue
        for folder, directories, files in os.walk(directory, followlinks=False):
            directories[:] = [d for d in directories if d not in GENERATED_DIRS]
            if any((Path(folder) / d).is_symlink() for d in directories):
                raise RuntimeError('Unexpected runtime source symlink in a core package.')
            paths.update(str((Path(folder) / f).relative_to(runtime)) for f in files if f.endswith('.py'))
    return paths


def _plan(runtime: Path, project: Path) -> tuple[dict, list[tuple[Path, bytes]], dict[Path, str | None]]:
    runtime = runtime.resolve()
    project = project.resolve()
    _assert_private(runtime, project)
    brand = json.loads((project / 'branding/brand.json').read_text())
    registry_bytes = (project / 'branding/runtime-literals.json').read_bytes()
    registry = json.loads(registry_bytes)
    if registry['upstream_commit'] != brand['runtime']['commit']:
        raise RuntimeError('The runtime branding registry and pinned runtime revision disagree.')
    if (runtime / '.git').exists():
        revision = subprocess.check_output(['git', '-C', str(runtime), 'rev-parse', 'HEAD'], text=True).strip()
        if revision != registry['upstream_commit']:
            raise RuntimeError('Runtime revision is not certified for this branding overlay. Run the documented setup.')
    previous_path = _checked_target(runtime, STAMP)
    previous_bytes = previous_path.read_bytes() if previous_path.exists() else None
    previous = json.loads(previous_bytes) if previous_bytes is not None else {}
    values = {'@@PRODUCT@@': brand['product']['display_name'],
              '@@PUBLISHER@@': brand['organization']['display_name']}
    if any(not isinstance(value, str) or not value or any(
            ch in '\\{}\r\n\'"' or ord(ch) < 32 or ord(ch) == 127 for ch in value)
           for value in values.values()):
        raise RuntimeError('Brand names used in runtime source must not contain quotes, braces, backslashes, or controls.')
    records = {record['path']: record for record in registry['files']}
    if len(records) != len(registry['files']):
        raise RuntimeError('Duplicate runtime source records are not supported.')
    expected = registry.get('source_sha256')
    if not isinstance(expected, dict) or not expected:
        raise RuntimeError('The pinned runtime source checksum inventory is missing.')
    unexpected = _core_source_paths(runtime) - expected.keys()
    if unexpected:
        raise RuntimeError(f'Unexpected runtime source: {sorted(unexpected)[0]}')
    checks = {previous_path: _hash(previous_bytes) if previous_bytes is not None else None}
    # This includes unpatched core Python modules in staged copies without .git.
    for relative, digest in expected.items():
        target = _checked_target(runtime, relative)
        if not target.is_file():
            raise RuntimeError(f'Missing pinned runtime source: {relative}')
        current_hash = _hash(target.read_bytes())
        checks[target] = current_hash
        if relative not in records and current_hash != digest:
            raise RuntimeError(f'Unrecognized runtime edits in {relative}; refusing to overwrite them.')
    files, regions, writes = {}, {}, []
    for relative, record in records.items():
        target = _checked_target(runtime, relative)
        if expected.get(relative) != record['upstream_sha256']:
            raise RuntimeError(f'The pinned runtime source checksum disagrees with the branding slot: {relative}')
        current = target.read_bytes()
        # Check the file did not change between the whole-source check and plan.
        if _hash(current) != checks[target]:
            raise RuntimeError(f'Unrecognized runtime edits in {relative}; refusing to overwrite them.')
        original = _pristine_source(record, current, previous)
        structured = record.get('format') in ('yaml', 'json')
        if record.get('format', 'python') not in ('python', 'yaml', 'json'):
            raise RuntimeError('Unsupported runtime branding source format.')
        spans = _ASSETS['yaml_spans'](original, record) if structured else _literal_spans(original)
        replacements = {}
        python_replacements = {}
        for slot in record['slots']:
            upstream = slot['upstream_literal']
            if upstream not in spans:
                raise RuntimeError(f'Branding slot no longer matches a complete pinned source expression: {relative}')
            replacement = slot['source_template']
            for key, value in values.items():
                replacement = replacement.replace(key, value)
            if '@@' in replacement:
                raise RuntimeError(f'Unresolved runtime branding template in {relative}')
            if not structured:
                _validate_slot(upstream, replacement, relative)
                position = _python_slot_span(original, spans[upstream], slot, relative)
                if position in python_replacements and python_replacements[position] != (upstream, replacement):
                    raise RuntimeError(f'Conflicting runtime branding slots in {relative}')
                python_replacements[position] = (upstream, replacement)
            else:
                if upstream in replacements and replacement != replacements[upstream]:
                    raise RuntimeError(f'Conflicting runtime branding slots in {relative}')
                replacements[upstream] = replacement
        edits = (sorted((start, end, upstream, replacements[upstream])
                        for upstream in replacements for start, end in spans[upstream]) if structured
                 else sorted((start, end, upstream, replacement)
                             for (start, end), (upstream, replacement) in python_replacements.items()))
        pieces, cursor, length = [], 0, 0
        regions[relative] = []
        for start, end, upstream, replacement in edits:
            if start < cursor:
                raise RuntimeError(f'Overlapping runtime branding slots in {relative}')
            before = original[cursor:start]
            pieces.extend((before, replacement))
            length += len(before)
            regions[relative].append({'start': length, 'end': length + len(replacement), 'original': upstream})
            length += len(replacement)
            cursor = end
        pieces.append(original[cursor:])
        source = ''.join(pieces)
        if structured:
            _ASSETS['validate_yaml_patch'](original, source, record)
        elif _structure(source) != _structure(original):
            raise RuntimeError(f'Runtime patch changes executable structure: {relative}')
        data = source.encode()
        files[relative] = _hash(data)
        if data != current:
            writes.append((target, data))
    stamp = {'schema_version': 1, 'upstream_commit': registry['upstream_commit'],
             'registry_sha256': _hash(registry_bytes),
             'brand_sha256': _hash(json.dumps(brand, sort_keys=True).encode()),
             'files': files, 'regions': regions}
    return stamp, writes, checks


def plan_runtime_branding(runtime: Path, *, project: Path = ROOT) -> tuple[dict, list[tuple[Path, bytes]]]:
    stamp, writes, _ = _plan(runtime, project)
    return stamp, writes


def _stage(target: Path, data: bytes, mode: int) -> Path:
    descriptor, name = tempfile.mkstemp(prefix=f'.{target.name}.altur-', dir=target.parent)
    path = Path(name)
    try:
        with os.fdopen(descriptor, 'wb') as output:
            output.write(data)
        path.chmod(mode)
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return path


def _write_checked(writes: list[tuple[Path, bytes | None]], checks: dict[Path, str | None]) -> None:
    """Prepare every temporary file and revalidate every source before writing."""
    staged, backups, committed = {}, {}, []
    try:
        for target, data in writes:
            before = target.read_bytes() if target.exists() else None
            mode = stat.S_IMODE(target.stat().st_mode) if target.exists() else 0o600
            backups[target] = (before, mode)
            staged[target] = _stage(target, data, mode) if data is not None else None
        for target, digest in checks.items():
            if target.is_symlink() or target.resolve() != target:
                raise RuntimeError('Runtime branding does not follow source or stamp symlinks.')
            actual = _hash(target.read_bytes()) if target.exists() else None
            if actual != digest:
                raise RuntimeError(f'Unrecognized runtime edits in {target.name}; refusing to overwrite them.')
        for target, _ in writes:
            temporary = staged[target]
            if temporary is None:
                target.unlink(missing_ok=True)
            else:
                os.replace(temporary, target)
            committed.append(target)
    except BaseException:
        for target in reversed(committed):
            before, mode = backups[target]
            if before is None:
                target.unlink(missing_ok=True)
            else:
                rollback = _stage(target, before, mode)
                try:
                    os.replace(rollback, target)
                finally:
                    rollback.unlink(missing_ok=True)
        raise
    finally:
        for temporary in staged.values():
            if temporary is not None:
                temporary.unlink(missing_ok=True)


def apply_runtime_branding(runtime: Path, *, project: Path = ROOT) -> dict:
    runtime = runtime.resolve()
    stamp, writes, checks = _plan(runtime, project)
    stamp_bytes = (json.dumps(stamp, sort_keys=True, indent=2) + '\n').encode()
    _write_checked([*writes, (runtime / STAMP, stamp_bytes)], checks)
    return stamp


def verify_runtime_branding(runtime: Path, *, project: Path = ROOT) -> dict:
    runtime = runtime.resolve()
    stamp, writes, _ = _plan(runtime, project)
    stored = json.loads((runtime / STAMP).read_text()) if (runtime / STAMP).exists() else None
    if writes or stored != stamp:
        raise RuntimeError('The runtime branding is out of date. Run the documented branding generation command.')
    return stamp


def restore_runtime_sources(runtime: Path, *, project: Path = ROOT) -> None:
    """Restore only checksum-matched owned patches before an explicit setup run."""
    runtime = runtime.resolve()
    _, _, checks = _plan(runtime, project)
    previous_path = runtime / STAMP
    previous = json.loads(previous_path.read_text()) if previous_path.exists() else {}
    registry = json.loads((project / 'branding/runtime-literals.json').read_text())
    writes = []
    for record in registry['files']:
        target = _checked_target(runtime, record['path'])
        current = target.read_bytes()
        original = _pristine_source(record, current, previous).encode()
        if original != current:
            writes.append((target, original))
    _write_checked([*writes, (previous_path, None)], checks)
