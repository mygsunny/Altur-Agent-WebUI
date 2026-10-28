"""Reviewed bundled defaults preserve localization contracts and custom layers."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest


REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('altur_runtime_locales', REPO / 'branding/runtime_locales.py')
locales = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(locales)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


@pytest.fixture
def project(tmp_path):
    root = tmp_path / 'portable-project'
    (root / 'branding').mkdir(parents=True)
    brand = {'runtime': {'commit': 'pinned-fixture'}, 'product': {'display_name': 'Altur-Agent'},
             'organization': {'display_name': 'ArtemisProject'}}
    (root / 'branding/brand.json').write_text(json.dumps(brand))
    catalogs = {
        'en': {'explainer.persistence.default': 'Hermes cannot save: {home}. Use `hermes doctor`.',
               'approval.header': 'Hermes asks permission', 'provider.label': 'Nous Portal',
               'technical': '`hermes doctor` ~/.hermes HERMES_HOME',
               'quoted.example': 'A quoted factual discussion about Hermes.'},
        'es': {'approval.header': 'Hermes pide permiso', 'provider.label': 'Nous Portal'},
    }
    edits = {
        'en': [('explainer.persistence.default', '@@PRODUCT@@ cannot save: {home}. Use `hermes doctor`.'),
               ('approval.header', '@@PRODUCT@@ asks permission')],
        'es': [('approval.header', '@@PRODUCT@@ pide permiso')],
    }
    registry = {'upstream_commit': 'pinned-fixture', 'languages': ['en', 'es'],
                'catalogs': {lang: {'messages': messages, 'baseline_sha256': digest(canonical(messages))}
                             for lang, messages in catalogs.items()},
                'edits': {lang: [{'key': key, 'upstream_value_sha256': digest(catalogs[lang][key].encode()),
                                  'value_template': template} for key, template in slots]
                          for lang, slots in edits.items()}}
    (root / 'branding/runtime-locales.json').write_text(json.dumps(registry))
    return root


def test_source_zip_generates_complete_catalogs_without_runtime_or_yaml_dependency(project):
    output = locales.generate_runtime_locales(project=project)
    en = json.loads((output / 'en.yaml').read_text())
    es = json.loads((output / 'es.yaml').read_text())
    assert en['explainer.persistence.default'] == 'Altur-Agent cannot save: {home}. Use `hermes doctor`.'
    assert es['approval.header'] == 'Altur-Agent pide permiso'
    for key, value in {
        'provider.label': 'Nous Portal', 'technical': '`hermes doctor` ~/.hermes HERMES_HOME',
        'quoted.example': 'A quoted factual discussion about Hermes.',
    }.items():
        assert en[key] == value
    assert not (project / '.runtime').exists()
    assert locales.verify_runtime_locales(project=project) == output


def test_regeneration_follows_manifest_and_never_edits_user_locales(project):
    output = locales.generate_runtime_locales(project=project)
    first = {path.name: path.read_bytes() for path in output.iterdir()}
    locales.generate_runtime_locales(project=project)
    assert {path.name: path.read_bytes() for path in output.iterdir()} == first
    user_locale = project / '.trial/agent-home/locales/en.yaml'
    user_locale.parent.mkdir(parents=True)
    user_locale.write_text('approval.header: My customer-authored Hermes label\n')
    original = user_locale.read_bytes()
    brand_path = project / 'branding/brand.json'
    brand = json.loads(brand_path.read_text())
    brand['product']['display_name'] = 'Future Agent'
    brand_path.write_text(json.dumps(brand))
    with pytest.raises(RuntimeError, match='outdated'):
        locales.verify_runtime_locales(project=project)
    locales.generate_runtime_locales(project=project)
    assert json.loads((output / 'en.yaml').read_text())['approval.header'] == 'Future Agent asks permission'
    assert user_locale.read_bytes() == original


@pytest.mark.parametrize('failure', ['catalog-hash', 'leaf-hash', 'format-field', 'command', 'token', 'duplicate', 'language', 'revision'])
def test_invalid_registry_never_changes_existing_outputs(project, failure):
    output = locales.generate_runtime_locales(project=project)
    before = {path.name: path.read_bytes() for path in output.iterdir()}
    path = project / 'branding/runtime-locales.json'
    registry = json.loads(path.read_text())
    slot = registry['edits']['en'][0]
    if failure == 'catalog-hash':
        registry['catalogs']['en']['messages']['provider.label'] = 'An unreviewed provider'
    elif failure == 'leaf-hash':
        slot['upstream_value_sha256'] = '0' * 64
    elif failure == 'format-field':
        slot['value_template'] = slot['value_template'].replace('{home}', '{unreviewed}')
    elif failure == 'command':
        slot['value_template'] = slot['value_template'].replace('hermes doctor', 'unreviewed install')
    elif failure == 'token':
        slot['value_template'] += ' @@UNKNOWN@@'
    elif failure == 'duplicate':
        registry['edits']['en'].append(dict(slot))
    elif failure == 'language':
        registry['languages'].append('../outside')
    else:
        registry['upstream_commit'] = 'different-revision'
    path.write_text(json.dumps(registry))
    with pytest.raises(RuntimeError):
        locales.generate_runtime_locales(project=project)
    assert {path.name: path.read_bytes() for path in output.iterdir()} == before


@pytest.mark.parametrize('target', ['directory', 'file'])
def test_generation_refuses_symlinks_and_preserves_external_files(project, tmp_path, target):
    outside = tmp_path / 'external'
    outside.mkdir()
    external_file = outside / 'en.yaml'
    external_file.write_text('Do not change this file.\n')
    output = project / 'branding/generated-locales'
    if target == 'directory':
        output.symlink_to(outside, target_is_directory=True)
    else:
        output.mkdir()
        (output / 'en.yaml').symlink_to(external_file)
    with pytest.raises(RuntimeError, match='checkout|symbolic'):
        locales.generate_runtime_locales(project=project)
    assert external_file.read_text() == 'Do not change this file.\n'


def test_all_17_catalogs_preserve_every_unreviewed_leaf_and_service_identity():
    registry = json.loads((REPO / 'branding/runtime-locales.json').read_text())
    _, artifacts = locales.plan_runtime_locales(project=REPO)
    assert len(registry['languages']) == 17
    for lang in registry['languages']:
        original = registry['catalogs'][lang]['messages']
        generated = json.loads(artifacts[f'{lang}.yaml'])
        approved = {slot['key'] for slot in registry['edits'][lang]}
        assert generated.keys() == original.keys()
        for key in original.keys() - approved:
            assert generated[key] == original[key], (lang, key)
    en = json.loads(artifacts['en.yaml'])
    assert en['gateway.credits.not_logged_in'] == registry['catalogs']['en']['messages']['gateway.credits.not_logged_in']
    assert 'Nous Research Hermes 3 & 4' in en['cli.banner.hermes_models_not_agentic']
    assert en['slash.wake.description'] == registry['catalogs']['en']['messages']['slash.wake.description']
    assert en['gateway.debug.share_hint'] == 'Use the bundled Help to find verified support instructions before sharing these reports.'


def test_real_runtime_yaml_reader_fallback_and_custom_layer_priority(project, tmp_path):
    runtime = REPO / '.runtime/hermes-agent'
    python = REPO / '.runtime/venv/bin/python'
    if not python.is_file() or not (runtime / 'agent/i18n.py').is_file():
        pytest.skip('Private runtime interpreter/source is needed for the real locale reader check')
    output = locales.generate_runtime_locales(project=project)
    fixture = tmp_path / 'runtime-reader'
    (fixture / 'agent').mkdir(parents=True)
    (fixture / 'agent/__init__.py').write_text('')
    for name in ('i18n.py', 'i18n_layers.py', 'i18n_languages.py'):
        shutil.copyfile(runtime / 'agent' / name, fixture / 'agent' / name)
    shutil.copyfile(runtime / 'hermes_yaml.py', fixture / 'hermes_yaml.py')
    (fixture / 'hermes_constants.py').write_text(
        'import os\ndef get_hermes_home():\n    return os.environ["HERMES_HOME"]\n'
    )
    home = tmp_path / 'user-home'
    home.mkdir()
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(('HERMES_', 'OPENAI_', 'ANTHROPIC_')) and not key.endswith('_API_KEY')}
    env.update(PYTHONPATH=str(fixture), HERMES_HOME=str(home), HERMES_BUNDLED_LOCALES=str(output))
    script = '''import json, os
from pathlib import Path
from agent.i18n import t, reset_language_cache
from agent import i18n_layers
assert t('explainer.persistence.default', lang='es', home='Discuss Hermes') == "Altur-Agent cannot save: Discuss Hermes. Use `hermes doctor`."
assert t('provider.label', lang='en') == 'Nous Portal'
assert t('technical', lang='en') == '`hermes doctor` ~/.hermes HERMES_HOME'
locale = Path(os.environ['HERMES_HOME']) / 'locales/en.yaml'
locale.parent.mkdir()
locale.write_text(json.dumps({'approval.header': 'Customer-authored Hermes label'}))
reset_language_cache()
assert t('approval.header', lang='en') == 'Customer-authored Hermes label'
i18n_layers.register_pack('en', 'core', {'approval.header': 'Plugin-authored Hermes label'}, source='fixture')
assert t('approval.header', lang='en') == 'Plugin-authored Hermes label'
assert json.loads(locale.read_text())['approval.header'] == 'Customer-authored Hermes label'
print('Real locale reader, English fallback, user overlay and plugin priority verified')
'''
    result = subprocess.run([str(python), '-c', script], cwd=fixture, env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'Real locale reader' in result.stdout
