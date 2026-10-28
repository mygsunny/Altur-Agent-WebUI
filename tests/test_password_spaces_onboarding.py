"""Preserve exact password characters through first-run collection and save."""
import json
from pathlib import Path
import subprocess

import pytest

from tests.test_7865_settings_default_provider_survives_qualified_save import NODE, NODE_BIN, _EXTRACTOR

pytestmark = pytest.mark.skipif(NODE is None, reason='node not on PATH')


@pytest.mark.parametrize('password', [' pass word ', ' ', '  ', 'mid dle', ''])
def test_first_run_password_spaces_survive_every_boundary(password):
    source = Path(__file__).resolve().parents[1] / 'static/onboarding.js'
    driver = _EXTRACTOR + r'''
const fs=require('fs'),src=fs.readFileSync(process.argv[1],'utf8'),expected=process.argv[2];
eval(extractAsyncFunction(src,'nextOnboardingStep'));
eval(extractAsyncFunction(src,'_saveOnboardingDefaults'));
eval(extractFunction(src,'_getOnboardingPasswordSummaryKey'));
global.ONBOARDING={steps:['password','review'],step:0,form:{workspace:'/isolated',model:'fixture',password:''},status:{settings:{password_enabled:false}}};
global.$=id=>id==='onboardingPasswordInput'?{value:expected}:null;
global._renderOnboardingSteps=()=>{};
global._renderOnboardingBody=()=>{};
global._setOnboardingNotice=()=>{};
global._getOnboardingWorkspaceChoices=()=>[{path:'/isolated'}];
global.localStorage={setItem(){}};
global.t=k=>k;
const posts=[];
global.api=async(path,opts)=>{posts.push({path,body:JSON.parse(opts.body)});return {auth_enabled:!!expected}};
(async()=>{
 await nextOnboardingStep();
 const collected=ONBOARDING.form.password===expected;
 const summary=_getOnboardingPasswordSummaryKey({password_enabled:false});
 await _saveOnboardingDefaults();
 const body=posts.find(p=>p.path==='/api/settings').body;
 process.stdout.write(JSON.stringify({collected,summary,preserved:body._set_password===expected,hasPassword:Object.prototype.hasOwnProperty.call(body,'_set_password')}));
})();
'''
    run = subprocess.run([NODE_BIN, '-e', driver, str(source), password],
                         capture_output=True, text=True, timeout=15)
    assert run.returncode == 0, run.stderr
    data = json.loads(run.stdout)
    assert data['collected']
    assert data['summary'] == ('onboarding_password_will_enable' if password else 'onboarding_password_remains_disabled')
    assert data['hasPassword'] == bool(password)
    if password:
        assert data['preserved']
