"""First-run password validation uses the server's advertised minimum."""
import json
from pathlib import Path
import subprocess

import pytest

from tests.test_7865_settings_default_provider_survives_qualified_save import NODE, NODE_BIN, _EXTRACTOR

pytestmark = pytest.mark.skipif(NODE is None, reason='node not on PATH')


@pytest.mark.parametrize('password, valid', [('abc', False), ('abcd', True),
                                         ('🔒🔒🔒', False), ('🔒🔒🔒🔒', True), ('', True)])
def test_first_run_validates_before_saving_any_defaults(password, valid):
    source = Path(__file__).resolve().parents[1] / 'static/onboarding.js'
    driver = _EXTRACTOR + r'''
const fs=require('fs');
eval(extractAsyncFunction(fs.readFileSync(process.argv[1],'utf8'),'_saveOnboardingDefaults'));
global.ONBOARDING={form:{workspace:'/isolated-workspace',model:'fixture',password:process.argv[2]},status:{settings:{password_min_length:4}}};
global._getOnboardingWorkspaceChoices=()=>[{path:'/isolated-workspace'}];
global.$=()=>null;
global.localStorage={setItem(){}};
global.t=k=>k+' {min}';
const posts=[];
global.api=async(path,opts)=>{posts.push({path,body:JSON.parse(opts.body)});return {auth_enabled:true}};
(async()=>{
 let error=null;
 try{await _saveOnboardingDefaults()}catch(e){error=e.message}
 process.stdout.write(JSON.stringify({error,count:posts.length,passwordSent:!!posts[0]?.body._set_password}));
})();
'''
    result = subprocess.run([NODE_BIN, '-e', driver, str(source), password],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    if valid:
        assert data['error'] is None and data['count'] == 1
        assert data['passwordSent'] == bool(password)
    else:
        assert data['count'] == 0 and '4' in data['error']
