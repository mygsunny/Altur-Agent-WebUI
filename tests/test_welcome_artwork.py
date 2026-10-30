"""Portable settings contract tests (no application runtime required)."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class ArtworkSettingsTests(unittest.TestCase):
    def test_defaults_and_validation_contract(self):
        tree = ast.parse((ROOT / 'api/config.py').read_text())
        values = {}
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and isinstance(node.value, ast.Dict) and target.id in ('_SETTINGS_DEFAULTS', '_SETTINGS_ENUM_VALUES', '_SETTINGS_INT_RANGES'):
                        values[target.id] = {
                            k.value: ast.literal_eval(v)
                            for k, v in zip(node.value.keys, node.value.values)
                            if isinstance(k, ast.Constant) and isinstance(k.value, str)
                            and k.value.startswith('welcome_')
                        }
        self.assertEqual(values['_SETTINGS_DEFAULTS'].get('welcome_artwork'), 'original')
        self.assertEqual(values['_SETTINGS_DEFAULTS']['welcome_artwork_height_desktop'], 240)
        self.assertEqual(values['_SETTINGS_DEFAULTS']['welcome_artwork_height_mobile'], 160)
        self.assertIs(values['_SETTINGS_DEFAULTS'].get('welcome_logo_glow'), True)
        for device in ('desktop', 'mobile'):
            self.assertEqual(values['_SETTINGS_DEFAULTS'].get('welcome_offset_' + device), 0)
            self.assertEqual(values['_SETTINGS_INT_RANGES'].get('welcome_offset_' + device), (-300, 300))
        self.assertEqual(set(values['_SETTINGS_ENUM_VALUES']['welcome_artwork']), {'none', 'original', 'photo'})
        for device in ('desktop', 'mobile'):
            self.assertEqual(values['_SETTINGS_INT_RANGES']['welcome_artwork_height_' + device], (64, 600))

if __name__ == '__main__':
    unittest.main()
