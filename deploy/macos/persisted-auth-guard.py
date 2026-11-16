"""Local fail-closed LAN prerequisite, independent of upstream permissive defaults."""
import json
import os
from pathlib import Path
import re
import stat

def require_persisted_auth(data):
    data = Path(data)
    for name in ('settings.json', '.pbkdf2_key', '.signing_key'):
        path = data / name
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError('Owner-only regular auth files required')
    settings = json.loads((data / 'settings.json').read_text())
    value = settings.get('password_hash') if isinstance(settings, dict) else None
    if not isinstance(value, str) or re.fullmatch(r'[0-9a-f]{64}', value) is None:
        raise ValueError('Valid native persisted password hash required')
    for name in ('.pbkdf2_key', '.signing_key'):
        if len((data / name).read_bytes()) < 32:
            raise ValueError('Existing authentication keys required')
    return value
