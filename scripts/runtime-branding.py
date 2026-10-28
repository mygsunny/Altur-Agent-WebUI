#!/usr/bin/env python3
"""Verify/apply reviewed display literals in a private pinned runtime copy."""
import argparse
from pathlib import Path
import sys
import runpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from branding.runtime import apply_runtime_branding, verify_runtime_branding, restore_runtime_sources

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('action', choices=['apply', 'verify', 'restore'])
p.add_argument('runtime', type=Path, nargs='?', default=ROOT/'.runtime/hermes-agent')
a = p.parse_args()
try:
    {'apply': apply_runtime_branding, 'verify': verify_runtime_branding,
     'restore': restore_runtime_sources}[a.action](a.runtime)
    locales = runpy.run_path(str(ROOT/'branding/runtime_locales.py'))
    if a.action == 'apply': locales['generate_runtime_locales'](project=ROOT)
    if a.action == 'verify': locales['verify_runtime_locales'](project=ROOT)
except (RuntimeError, OSError, ValueError) as exc:
    p.exit(1, f'Runtime branding: {exc}\n')
print(f'Runtime display sources: {a.action} succeeded')
