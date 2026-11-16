"""Altru moved upstream's inline theme/skin bootstrap into static/appearance.js.

Upstream adds skins to its inline script and to the server allowlist; this keeps
our copy from silently falling behind after an upstream merge.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_appearance_js_skin_list_matches_server_allowlist():
    from api.config import _SETTINGS_SKIN_VALUES

    source = (ROOT / 'static/appearance.js').read_text(encoding='utf-8')
    match = re.search(r"const skins = new Set\(\[([^\]]*)\]\)", source)
    assert match, 'skin allowlist not found in static/appearance.js'
    client = set(re.findall(r"'([a-z0-9-]+)'", match.group(1)))
    # Upstream's browser list also carries a few extension skins the server
    # does not persist, so every server skin must be known client-side.
    missing = set(_SETTINGS_SKIN_VALUES) - client
    assert not missing, f'add to static/appearance.js: {sorted(missing)}'


def test_index_html_loads_appearance_before_stylesheet():
    html = (ROOT / 'static/index.html').read_text(encoding='utf-8')
    assert html.index('static/appearance.js') < html.index('static/style.css')
