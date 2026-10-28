"""Portable display branding, separate from protocol and storage identity."""
import json
from pathlib import Path
BRAND = json.loads((Path(__file__).resolve().parents[1] / "branding/brand.json").read_text())

for _field in ('identity_instruction', 'customer_guidance_instruction'):
    BRAND['assistant'][_field] = BRAND['assistant'][_field].format(product=BRAND['product']['display_name'], publisher=BRAND['organization']['display_name'])


def assistant_name_managed():
    """Presentation policy only; never changes stored identities or user text."""
    return BRAND.get('ui', {}).get('assistant_name_mode') == 'brand'
