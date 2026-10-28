"""Exercise the real settings save functions with disposable DOM credentials."""
import json
import subprocess

import pytest

from tests.test_7865_settings_default_provider_survives_qualified_save import (
    NODE, NODE_BIN, PANELS_JS, UI_JS, _DRIVER,
)

pytestmark = pytest.mark.skipif(NODE is None, reason='node not on PATH')


def run_case(case):
    prefix = _DRIVER.split('(async () => {', 1)[0]
    driver = prefix + r'''
const scenario=process.argv[3];
global._settingsHermesDefaultModelOnOpen=QUALIFIED;
global._settingsHermesDefaultModelProviderOnOpen=PROVIDER;
global._settingsPasswordAuthEnabled=true;
global._settingsPasswordEnvLocked=scenario==='locked';
els.settingsPassword={value:'fixture-new',minLength:4,focus(){this.focused=true}};
els.settingsCurrentPassword={value:'fixture-current',focus(){this.focused=true}};
global._renderSettingsAuthStatus=()=>{};
global._updateAuthWarningBadge=()=>{};
global._updateAuthDisabledWarning=()=>{};
global._enqueueSettingsPost=async opts=>{
  const body=JSON.parse(opts.body);
  posts.push({url:'/api/settings',body});
  if(scenario==='incorrect') throw new Error('Current password is incorrect.');
  return {password_auth_enabled:true,auth_enabled:true};
};
if(['blank','general-current','general-empty'].includes(scenario)) els.settingsPassword.value='';
if(['missing-current','general-empty','first'].includes(scenario)) els.settingsCurrentPassword.value='';
if(scenario==='first')global._settingsPasswordAuthEnabled=false;
if(scenario==='short')els.settingsPassword.value='abc';
(async()=>{
  if(scenario.startsWith('general-')) await saveSettings(false);
  else {
    eval(extractAsyncFunction(panelsSrc,'changeSettingsPassword'));
    await changeSettingsPassword();
  }
  const post=posts.find(p=>p.url==='/api/settings');
  process.stdout.write(JSON.stringify({
    count:posts.length,toasts,
    newSent:!!post&&post.body._set_password==='fixture-new',
    currentSent:!!post&&post.body._current_password==='fixture-current',
    hasCurrent:!!post&&Object.prototype.hasOwnProperty.call(post.body,'_current_password'),
    cleared:els.settingsPassword.value===''&&els.settingsCurrentPassword.value==='',
    newFocused:!!els.settingsPassword.focused,
    currentFocused:!!els.settingsCurrentPassword.focused,
    retained:els.settingsPassword.value==='fixture-new'
  }));
})().catch(e=>{console.error(e.message);process.exit(1)});
'''
    result = subprocess.run([NODE_BIN, '-e', driver, str(PANELS_JS), str(UI_JS), case],
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_general_save_reports_password_unchanged_when_only_current_is_present():
    result = run_case('general-current')
    assert result['toasts'][-1] == 'settings_saved_password_unchanged'
    assert not result['newSent']


def test_general_save_without_password_edits_keeps_normal_confirmation():
    assert run_case('general-empty')['toasts'][-1] == 'settings_saved'


def test_dedicated_change_refuses_blank_new_password_without_a_request():
    result = run_case('blank')
    assert result['count'] == 0
    assert result['newFocused']
    assert result['toasts'][-1] == 'new_password_required'


def test_dedicated_change_refuses_short_password_without_a_request():
    result = run_case('short')
    assert result['count'] == 0 and result['newFocused']
    assert result['toasts'][-1] == 'new_password_min_length'


def test_dedicated_change_uses_existing_authenticated_save_path():
    result = run_case('valid')
    assert result['newSent'] and result['currentSent']
    assert result['cleared']
    assert result['toasts'][-1] == 'settings_saved_pw_updated'


def test_dedicated_change_still_requires_current_password():
    result = run_case('missing-current')
    assert result['count'] == 0 and result['currentFocused']
    assert result['toasts'][-1] == 'current_password_required'


def test_rejected_change_keeps_fields_for_correction():
    result = run_case('incorrect')
    assert result['retained'] and not result['cleared']
    assert 'Current password is incorrect.' in result['toasts'][-1]


def test_environment_locked_password_cannot_be_changed():
    result = run_case('locked')
    assert result['count'] == 0
    assert result['toasts'][-1] == 'password_env_var_locked'


def test_first_password_creation_does_not_send_current_password():
    result = run_case('first')
    assert result['newSent'] and not result['hasCurrent']
