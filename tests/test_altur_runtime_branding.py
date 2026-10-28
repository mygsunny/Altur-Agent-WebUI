"""Private runtime source branding is reversible and cannot become an output filter."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('altur_runtime_branding', ROOT / 'branding/runtime.py')
branding = importlib.util.module_from_spec(spec)
spec.loader.exec_module(branding)


def fixture_project(tmp_path, source=None, slots=None):
    source = source or '''IDENTITY = "You are Hermes Agent"
TECHNICAL_MARKER = "# Hermes runtime environment"
def reply(user):
    return IDENTITY + ': ' + user
'''
    project = tmp_path / 'project'
    runtime = project / '.runtime/agent'
    runtime.mkdir(parents=True)
    (project / 'branding').mkdir()
    (runtime / 'display.py').write_text(source)
    brand = {'product': {'display_name': 'Altur-Agent'}, 'organization': {'display_name': 'ArtemisProject'},
             'runtime': {'commit': 'fixture-revision'}}
    (project / 'branding/brand.json').write_text(json.dumps(brand))
    digest = hashlib.sha256(source.encode()).hexdigest()
    registry = {'upstream_commit': 'fixture-revision', 'source_sha256': {'display.py': digest}, 'files': [{
        'path': 'display.py', 'upstream_sha256': digest,
        'slots': slots or [{'upstream_literal': '"You are Hermes Agent"', 'source_template': '"You are @@PRODUCT@@"'}]}]}
    (project / 'branding/runtime-literals.json').write_text(json.dumps(registry))
    return project, runtime, source


def test_private_source_changes_before_user_interpolation(tmp_path):
    project, runtime, source = fixture_project(tmp_path)
    branding.apply_runtime_branding(runtime, project=project)
    scope = {}
    exec((runtime / 'display.py').read_text(), scope)
    assert scope['reply']('Discuss Hermes, NousResearch and nesquena.') == (
        'You are Altur-Agent: Discuss Hermes, NousResearch and nesquena.')
    assert scope['TECHNICAL_MARKER'] == '# Hermes runtime environment'
    branding.verify_runtime_branding(runtime, project=project)


def test_repeat_regenerate_name_and_restore_are_exact(tmp_path):
    project, runtime, source = fixture_project(tmp_path)
    first = branding.apply_runtime_branding(runtime, project=project)
    assert first == branding.apply_runtime_branding(runtime, project=project)
    p = project / 'branding/brand.json'
    brand = json.loads(p.read_text())
    brand['product']['display_name'] = 'Example Agent'
    p.write_text(json.dumps(brand))
    with pytest.raises(RuntimeError, match='out of date'):
        branding.verify_runtime_branding(runtime, project=project)
    branding.apply_runtime_branding(runtime, project=project)
    assert 'You are Example Agent' in (runtime / 'display.py').read_text()
    branding.restore_runtime_sources(runtime, project=project)
    assert (runtime / 'display.py').read_text() == source


def update_registry(project, mutate):
    path = project / 'branding/runtime-literals.json'
    registry = json.loads(path.read_text())
    mutate(registry)
    path.write_text(json.dumps(registry))


def test_f_string_executable_arguments_cannot_be_rewritten(tmp_path):
    source = '''def reply(user):
    return f"Hermes: {user.replace('Hermes', 'Nous')}"
'''
    project, runtime, _ = fixture_project(tmp_path, source, [{
        'upstream_literal': '''f"Hermes: {user.replace('Hermes', 'Nous')}"''',
        'source_template': '''f"@@PRODUCT@@: {user.replace('Altur-Agent', 'ArtemisProject')}"''',
    }])
    with pytest.raises(RuntimeError, match='executable structure'):
        branding.apply_runtime_branding(runtime, project=project)
    assert (runtime / 'display.py').read_text() == source
    assert not (runtime / branding.STAMP).exists()


def test_slots_match_complete_ast_expressions_not_comments_or_substrings(tmp_path):
    source = '''IDENTITY = "You are Hermes Agent"
# example source literal: "You are Hermes Agent"
DOCUMENT = '\\'"You are Hermes Agent"\\''
'''
    project, runtime, _ = fixture_project(tmp_path, source)
    branding.apply_runtime_branding(runtime, project=project)
    result = (runtime / 'display.py').read_text()
    assert 'IDENTITY = "You are Altur-Agent"' in result
    assert '# example source literal: "You are Hermes Agent"' in result
    assert '''DOCUMENT = '\\'"You are Hermes Agent"\\''''' in result


def test_stamp_symlink_cannot_write_outside_runtime(tmp_path):
    project, runtime, source = fixture_project(tmp_path)
    outside = tmp_path / 'outside.json'
    outside.write_text('{}')
    (runtime / branding.STAMP).symlink_to(outside)
    with pytest.raises(RuntimeError, match='symlink'):
        branding.apply_runtime_branding(runtime, project=project)
    assert outside.read_text() == '{}'
    assert (runtime / 'display.py').read_text() == source


def test_predictable_temporary_symlink_is_never_followed(tmp_path):
    project, runtime, _ = fixture_project(tmp_path)
    outside = tmp_path / 'outside.py'
    outside.write_text('# untouched\n')
    (runtime / 'display.py.altur-tmp').symlink_to(outside)
    branding.apply_runtime_branding(runtime, project=project)
    assert outside.read_text() == '# untouched\n'
    assert not (runtime / 'display.py').is_symlink()


def test_unpatched_core_source_hash_is_verified_without_git(tmp_path):
    project, runtime, source = fixture_project(tmp_path)
    other = runtime / 'agent/other.py'
    other.parent.mkdir()
    pristine = 'ENABLED = True\n'
    other.write_text(pristine)
    update_registry(project, lambda r: r['source_sha256'].update({
        'agent/other.py': hashlib.sha256(pristine.encode()).hexdigest()}))
    other.write_text('ENABLED = False\n')
    with pytest.raises(RuntimeError, match='Unrecognized runtime edits'):
        branding.apply_runtime_branding(runtime, project=project)
    assert (runtime / 'display.py').read_text() == source
    assert not (runtime / branding.STAMP).exists()


def test_unknown_core_python_files_are_rejected_but_extension_files_are_not(tmp_path):
    project, runtime, source = fixture_project(tmp_path)
    (runtime / 'agent').mkdir()
    extra = runtime / 'agent/unexpected.py'
    extra.write_text('# operator code\n')
    with pytest.raises(RuntimeError, match='Unexpected runtime source'):
        branding.apply_runtime_branding(runtime, project=project)
    assert (runtime / 'display.py').read_text() == source
    extra.unlink()
    plugin = runtime / 'plugins/customer/custom.py'
    plugin.parent.mkdir(parents=True)
    plugin.write_text('# extension code\n')
    branding.apply_runtime_branding(runtime, project=project)
    assert plugin.read_text() == '# extension code\n'


@pytest.mark.parametrize('name', ['bad"; print("injected") #', 'bad{expression}', 'bad\\escape', 'bad\nname'])
def test_brand_name_injection_fails_before_any_writes(tmp_path, name):
    project, runtime, source = fixture_project(tmp_path)
    path = project / 'branding/brand.json'
    brand = json.loads(path.read_text())
    brand['product']['display_name'] = name
    path.write_text(json.dumps(brand))
    with pytest.raises(RuntimeError, match='Brand names'):
        branding.apply_runtime_branding(runtime, project=project)
    assert (runtime / 'display.py').read_text() == source
    assert not (runtime / branding.STAMP).exists()


def test_lexical_traversal_slot_is_rejected_even_when_it_resolves_inside(tmp_path):
    project, runtime, source = fixture_project(tmp_path)
    update_registry(project, lambda r: r['files'][0].update(path='../agent/display.py'))
    with pytest.raises(RuntimeError, match='escapes|relative'):
        branding.apply_runtime_branding(runtime, project=project)
    assert (runtime / 'display.py').read_text() == source


def test_failed_staging_never_changes_any_source(tmp_path, monkeypatch):
    project, runtime, source = fixture_project(tmp_path)
    stage = branding._stage

    def fail_stamp(target, data, mode):
        if target.name == branding.STAMP:
            raise OSError('fixture disk failure')
        return stage(target, data, mode)

    monkeypatch.setattr(branding, '_stage', fail_stamp)
    with pytest.raises(OSError, match='fixture disk failure'):
        branding.apply_runtime_branding(runtime, project=project)
    assert (runtime / 'display.py').read_text() == source
    assert not (runtime / branding.STAMP).exists()
    assert not list(runtime.glob('.*.altur-*'))


def test_failed_stamp_commit_rolls_source_back_exactly(tmp_path, monkeypatch):
    project, runtime, source = fixture_project(tmp_path)
    replace = branding.os.replace

    def fail_stamp(temporary, target):
        if target.name == branding.STAMP:
            raise OSError('fixture commit failure')
        return replace(temporary, target)

    monkeypatch.setattr(branding.os, 'replace', fail_stamp)
    with pytest.raises(OSError, match='fixture commit failure'):
        branding.apply_runtime_branding(runtime, project=project)
    assert (runtime / 'display.py').read_text() == source
    assert not (runtime / branding.STAMP).exists()


def test_edit_during_staging_is_preserved_without_partial_application(tmp_path, monkeypatch):
    project, runtime, source = fixture_project(tmp_path)
    stage = branding._stage
    operator_source = source + '# concurrent operator edit\n'

    def edit_during_stage(target, data, mode):
        staged = stage(target, data, mode)
        if target.name == 'display.py':
            target.write_text(operator_source)
        return staged

    monkeypatch.setattr(branding, '_stage', edit_during_stage)
    with pytest.raises(RuntimeError, match='Unrecognized runtime edits'):
        branding.apply_runtime_branding(runtime, project=project)
    assert (runtime / 'display.py').read_text() == operator_source
    assert not (runtime / branding.STAMP).exists()


def test_source_symlink_even_inside_private_tree_is_rejected(tmp_path):
    project, runtime, source = fixture_project(tmp_path)
    actual = runtime / 'real.txt'
    actual.write_text(source)
    (runtime / 'display.py').unlink()
    (runtime / 'display.py').symlink_to(actual)
    with pytest.raises(RuntimeError, match='symlink'):
        branding.apply_runtime_branding(runtime, project=project)
    assert actual.read_text() == source


def test_plain_format_fields_and_nested_f_string_literals_remain_contracts(tmp_path):
    source = 'MESSAGE = "Hermes {provider}"\n'
    project, runtime, _ = fixture_project(tmp_path, source, [{
        'upstream_literal': '"Hermes {provider}"',
        'source_template': '"@@PRODUCT@@ {provider.__class__}"',
    }])
    with pytest.raises(RuntimeError, match='executable structure'):
        branding.apply_runtime_branding(runtime, project=project)
    assert (runtime / 'display.py').read_text() == source


def test_valid_f_string_with_unicode_preserves_code_and_restores(tmp_path):
    source = '''PREFIX = 'é'; MESSAGE = f"Hermes: {lookup('Hermes')}"
'''
    project, runtime, _ = fixture_project(tmp_path, source, [{
        'upstream_literal': '''f"Hermes: {lookup('Hermes')}"''',
        'source_template': '''f"@@PRODUCT@@: {lookup('Hermes')}"''',
    }])
    branding.apply_runtime_branding(runtime, project=project)
    assert (runtime / 'display.py').read_text() == '''PREFIX = 'é'; MESSAGE = f"Altur-Agent: {lookup('Hermes')}"
'''
    branding.restore_runtime_sources(runtime, project=project)
    assert (runtime / 'display.py').read_text() == source


def test_coordinate_slot_leaves_identical_protocol_key_unchanged(tmp_path):
    source = 'DISPLAY = "Hermes"\nPROTOCOL = {"Hermes": "payload"}\n'
    project, runtime, _ = fixture_project(tmp_path, source, [{
        'upstream_literal': '"Hermes"', 'source_template': '"@@PRODUCT@@"',
        'line': 1, 'column': 10,
    }])
    branding.apply_runtime_branding(runtime, project=project)
    scope = {}
    exec((runtime / 'display.py').read_text(), scope)
    assert scope['DISPLAY'] == 'Altur-Agent'
    assert scope['PROTOCOL'] == {'Hermes': 'payload'}
    branding.verify_runtime_branding(runtime, project=project)
    branding.restore_runtime_sources(runtime, project=project)
    assert (runtime / 'display.py').read_text() == source


def test_duplicate_expression_requires_coordinates_for_legacy_registry(tmp_path):
    source = 'DISPLAY = "Hermes"\nPROTOCOL_KEY = "Hermes"\n'
    project, runtime, _ = fixture_project(tmp_path, source, [{
        'upstream_literal': '"Hermes"', 'source_template': '"@@PRODUCT@@"',
    }])
    with pytest.raises(RuntimeError, match='[Aa]mbiguous|coordinates|line and.*column'):
        branding.apply_runtime_branding(runtime, project=project)
    assert (runtime / 'display.py').read_text() == source
    assert not (runtime / branding.STAMP).exists()


@pytest.mark.parametrize('coordinates', [
    {'line': 1}, {'column': 10}, {'line': 2, 'column': 11},
    {'line': 999, 'column': 10}, {'line': True, 'column': 10},
])
def test_missing_or_inexact_coordinates_fail_before_writes(tmp_path, coordinates):
    source = 'DISPLAY = "Hermes"\nPROTOCOL_KEY = "Hermes"\n'
    project, runtime, _ = fixture_project(tmp_path, source, [{
        'upstream_literal': '"Hermes"', 'source_template': '"@@PRODUCT@@"', **coordinates,
    }])
    with pytest.raises(RuntimeError, match='coordinates|line|column'):
        branding.apply_runtime_branding(runtime, project=project)
    assert (runtime / 'display.py').read_text() == source
    assert not (runtime / branding.STAMP).exists()


def test_distinct_same_line_slots_can_have_different_replacements(tmp_path):
    source = 'DISPLAY = "Hermes"; ASSISTANT = "Hermes"; PROTOCOL_KEY = "Hermes"\n'
    first = source.index('"Hermes"')
    second = source.index('"Hermes"', first + 1)
    project, runtime, _ = fixture_project(tmp_path, source, [
        {'upstream_literal': '"Hermes"', 'source_template': '"@@PRODUCT@@"',
         'line': 1, 'column': first},
        {'upstream_literal': '"Hermes"', 'source_template': '"Assistant"',
         'line': 1, 'column': second},
    ])
    branding.apply_runtime_branding(runtime, project=project)
    scope = {}
    exec((runtime / 'display.py').read_text(), scope)
    assert (scope['DISPLAY'], scope['ASSISTANT'], scope['PROTOCOL_KEY']) == ('Altur-Agent', 'Assistant', 'Hermes')


def test_coordinate_column_uses_utf8_bytes(tmp_path):
    source = 'PREFIX = "é"; DISPLAY = "Hermes"; PROTOCOL_KEY = "Hermes"\n'
    first = source.index('"Hermes"')
    byte_column = len(source[:first].encode('utf-8'))
    project, runtime, _ = fixture_project(tmp_path, source, [{
        'upstream_literal': '"Hermes"', 'source_template': '"@@PRODUCT@@"',
        'line': 1, 'column': byte_column,
    }])
    branding.apply_runtime_branding(runtime, project=project)
    assert (runtime / 'display.py').read_text().count('"Altur-Agent"') == 1
    assert 'PROTOCOL_KEY = "Hermes"' in (runtime / 'display.py').read_text()


def test_old_all_occurrences_stamp_can_restore_excluded_literal_on_regeneration(tmp_path):
    source = 'DISPLAY = "Hermes"\nPROTOCOL_KEY = "Hermes"\n'
    project, runtime, _ = fixture_project(tmp_path, source, [{
        'upstream_literal': '"Hermes"', 'source_template': '"@@PRODUCT@@"',
        'line': 1, 'column': 10,
    }])
    # Simulate the earlier helper's recorded source-only overlay. New planning
    # reconstructs exact upstream bytes before selecting the newly scoped slot.
    prior = source.replace('"Hermes"', '"Old Product"')
    regions = []
    cursor = 0
    while (position := prior.find('"Old Product"', cursor)) != -1:
        regions.append({'start': position, 'end': position + len('"Old Product"'), 'original': '"Hermes"'})
        cursor = position + 1
    (runtime / 'display.py').write_text(prior)
    (runtime / branding.STAMP).write_text(json.dumps({
        'files': {'display.py': hashlib.sha256(prior.encode()).hexdigest()},
        'regions': {'display.py': regions},
    }))
    branding.apply_runtime_branding(runtime, project=project)
    assert (runtime / 'display.py').read_text() == 'DISPLAY = "Altur-Agent"\nPROTOCOL_KEY = "Hermes"\n'
    branding.restore_runtime_sources(runtime, project=project)
    assert (runtime / 'display.py').read_text() == source


def test_unrecognized_source_edits_are_never_overwritten(tmp_path):
    project, runtime, source = fixture_project(tmp_path)
    branding.apply_runtime_branding(runtime, project=project)
    path = runtime / 'display.py'
    path.write_text(path.read_text() + '\n# operator modification\n')
    before = path.read_bytes()
    with pytest.raises(RuntimeError, match='Unrecognized runtime edits'):
        branding.apply_runtime_branding(runtime, project=project)
    assert path.read_bytes() == before


def test_scope_and_executable_structure_are_guarded(tmp_path):
    project, runtime, source = fixture_project(tmp_path)
    with pytest.raises(RuntimeError, match='private runtime'):
        branding.apply_runtime_branding(tmp_path, project=project)
    path = project / 'branding/runtime-literals.json'
    registry = json.loads(path.read_text())
    registry['files'][0]['slots'][0]['source_template'] = '42'
    path.write_text(json.dumps(registry))
    with pytest.raises(RuntimeError, match='executable structure'):
        branding.apply_runtime_branding(runtime, project=project)
    assert (runtime / 'display.py').read_text() == source
