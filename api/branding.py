"""Portable display branding, separate from protocol and storage identity."""
import json
from pathlib import Path
BRAND = json.loads((Path(__file__).resolve().parents[1] / "branding/brand.json").read_text())

for _field in ('identity_instruction', 'customer_guidance_instruction'):
    BRAND['assistant'][_field] = BRAND['assistant'][_field].format(product=BRAND['product']['display_name'], publisher=BRAND['organization']['display_name'])


def resolve_assistant_name(value=None):
    """Server-owned assistant identity; product branding is only the fallback."""
    return str(value or '').strip() or BRAND['assistant']['display_name']


def assistant_identity_instruction(name=None):
    name = resolve_assistant_name(name)
    if name == BRAND['assistant']['display_name']:
        return BRAND['assistant']['identity_instruction']
    return BRAND['assistant']['named_identity_instruction'].format(
        assistant_name=name, product=BRAND['product']['display_name'],
        publisher=BRAND['organization']['display_name'])
