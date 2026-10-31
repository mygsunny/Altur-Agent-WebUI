"""Opt-in synthetic one-owner proof. Never opens an existing user's document."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api.cowork_sync import OfficeSync


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--test-parent', type=Path, required=True)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--fixture', type=Path, required=True)
    args = parser.parse_args()
    root = args.test_parent / ('cowork-oneowner-proof-' + uuid.uuid4().hex)
    root.mkdir(mode=0o700)
    data = args.fixture.read_bytes()
    sync = OfficeSync(args.state.resolve(), {'default': str(root)})
    extension = args.fixture.suffix[1:]
    first = sync.exchange('default', 'synthetic', dict(action='publish', extension=extension,
                                                     bytes=base64.b64encode(data).decode(), base=None))
    offered = sync.exchange('default', 'synthetic', dict(action='resume', owner='proof'))
    if offered['state'] != 'external':
        print(json.dumps({'proof_directory': str(root), 'resume': offered}))
        raise SystemExit(1)
    sync.exchange('default', 'synthetic', dict(action='accept', owner='proof', hash=offered['hash'],
                                             offer_id=offered['offer_id'], native_hash='proof'))
    result = sync.exchange('default', 'synthetic', dict(action='owner-publish', owner='proof',
                           connection_grant=offered['offer_id'], bytes=base64.b64encode(data).decode(), base=first['hash'], native_hash='proof'))
    target = root / ('synthetic.' + extension)
    assert target.read_bytes() == data
    assert result['state'] == 'synced'
    print(json.dumps({'proof_directory': str(root), 'samefile_native_publication': result['state'],
                      'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                      'cloud_upload': 'not established by local readback', 'receiving_device': 'not tested'}))


if __name__ == '__main__':
    main()
