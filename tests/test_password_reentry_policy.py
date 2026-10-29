"""Authenticated password changes need no reentry; disabling auth still does.

Uses the real route guard AST and the existing real-function Settings JS driver.
Only disposable fixture values are used; no user authentication state is read.
"""
import ast
from pathlib import Path
import shutil
import subprocess
import unittest
import json
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def guard_result(*, signed_in=True, current=None, clear=False):
    tree = ast.parse((ROOT / 'api/routes.py').read_text())
    guard = next(node for node in ast.walk(tree) if isinstance(node, ast.If)
                 and ast.unparse(node.test) == 'auth_enabled_before and password_auth_enabled_before and (requested_password or requested_clear_password)')
    wrapper = ast.parse('def check():\n    return True\n')
    function = wrapper.body[0]
    assert isinstance(function, ast.FunctionDef)
    function.body.insert(0, guard)
    env: dict[str, Any] = dict(auth_enabled_before=True, password_auth_enabled_before=True,
               requested_password=not clear, requested_clear_password=clear,
               current_password=current, logged_in_before=signed_in, handler=None,
               bad=lambda handler, message, code: (code, message),
               verify_password=lambda value: value == 'fixture-current')
    exec(compile(ast.fix_missing_locations(wrapper), '<real settings auth guard>', 'exec'), env)
    return env['check']()


def js_driver_prefix():
    # Read only the existing literal driver definitions, without importing pytest.
    tree = ast.parse((ROOT / 'tests/test_7865_settings_default_provider_survives_qualified_save.py').read_text())
    values = {}
    def value(node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return values[node.id]
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return value(node.left) + value(node.right)
        raise ValueError('Expected a literal driver')
    for statement in tree.body:
        if isinstance(statement, ast.Assign) and isinstance(statement.targets[0], ast.Name):
            name = statement.targets[0].id
            if name in ('_EXTRACTOR', '_DRIVER'):
                values[name] = value(statement.value)
    return values['_DRIVER'].split('(async () => {', 1)[0]


class PasswordReentryPolicyTests(unittest.TestCase):
    def test_signed_in_user_can_change_password_without_reentry(self):
        self.assertIs(guard_result(), True)

    def test_unsigned_request_still_needs_current_password(self):
        self.assertEqual(guard_result(signed_in=False)[0], 403)

    def test_disabling_auth_still_needs_current_password(self):
        self.assertEqual(guard_result(clear=True)[0], 403)
        self.assertIs(guard_result(clear=True, current='fixture-current'), True)

    def test_optional_supplied_password_is_still_verified(self):
        self.assertIs(guard_result(current='fixture-current'), True)
        self.assertEqual(guard_result(current='fixture-wrong')[0], 403)

    @unittest.skipUnless(shutil.which('node'), 'Node is needed for the real Settings save driver')
    def test_settings_sends_new_password_with_optional_current_password_blank(self):
        driver = js_driver_prefix() + r'''
global._settingsHermesDefaultModelOnOpen=QUALIFIED;
global._settingsHermesDefaultModelProviderOnOpen=PROVIDER;
global._settingsPasswordAuthEnabled=true;
global._settingsPasswordEnvLocked=false;
els.settingsPassword={value:'fixture-new',focus(){}};
els.settingsCurrentPassword={value:'',focus(){}};
global._renderSettingsAuthStatus=()=>{};
global._updateAuthWarningBadge=()=>{};
global._updateAuthDisabledWarning=()=>{};
global._enqueueSettingsPost=async opts=>{
  posts.push({url:'/api/settings',body:JSON.parse(opts.body)});
  return {password_auth_enabled:true,auth_enabled:true};
};
(async()=>{
  await saveSettings(false);
  const post=posts.find(p=>p.url==='/api/settings');
  process.stdout.write(JSON.stringify({sent:!!post&&post.body._set_password==='fixture-new',
    hasCurrent:!!post&&Object.hasOwn(post.body,'_current_password'),toasts}));
})().catch(e=>{console.error(e.message);process.exit(1)});
'''
        node = shutil.which('node')
        assert node is not None
        result = subprocess.run([node, '-e', driver,
                                 str(ROOT / 'static/panels.js'), str(ROOT / 'static/ui.js')],
                                capture_output=True, text=True, timeout=20, check=True)
        payload = json.loads(result.stdout)
        self.assertTrue(payload['sent'], 'Settings blocked a signed-in password change without reentry')
        self.assertFalse(payload['hasCurrent'], 'Blank optional current password should be omitted')
        self.assertEqual(payload['toasts'][-1], 'settings_saved_pw_updated')


if __name__ == '__main__':
    unittest.main()
