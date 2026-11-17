"""One cooperating editor at a time; real directory and durable sync database."""
import base64
import pytest
import sys
pytestmark = pytest.mark.skipif(sys.platform != 'darwin', reason='real macOS native coordination required')
from api.cowork import Conflict
from api.cowork_sync import OfficeSync
import io
import zipfile


def office(text='one'):
    b = io.BytesIO()
    with zipfile.ZipFile(b, 'w') as z:
        z.writestr(zipfile.ZipInfo('[Content_Types].xml'), '<Types/>')
        z.writestr(zipfile.ZipInfo('word/document.xml'), '<document>' + text + '</document>')
    return base64.b64encode(b.getvalue()).decode()


def test_handoff_restart_and_samefile(tmp_path):
    root = tmp_path / 'shared'; root.mkdir()
    state = tmp_path / 'state'
    sync = OfficeSync(state, {'default': str(root)})
    first = sync.exchange('default', 'doc', dict(action='publish', extension='docx', bytes=office(), base=None))
    call = lambda action, **kw: sync.exchange('default', 'doc', dict(action=action, owner='browser', **kw))
    assert call('owner-status')['ownership'] == 'external'
    offer = call('resume')
    assert offer['state'] == 'external'
    assert call('accept', hash=offer['hash'], offer_id=offer['offer_id'], native_hash='native')['state'] == 'synced'
    assert call('owner-status')['ownership'] == 'webui'
    changed = call('owner-publish', connection_grant=offer['offer_id'], base=first['hash'], bytes=office('webui'), native_hash='next')
    assert changed['filename'] == 'doc.docx'
    assert (root / 'doc.docx').read_bytes() == base64.b64decode(office('webui'))
    assert call('yield')['ownership'] == 'external'
    with pytest.raises(Conflict):
        call('owner-publish', base=changed['hash'], bytes=office('refused'))
    (root / 'doc.docx').write_bytes(base64.b64decode(office('external')))
    assert call('resume')['state'] == 'settling'
    offered = call('resume')
    call('accept', hash=offered['hash'], offer_id=offered['offer_id'], native_hash='external-native')
    # Reconstructed service in the same process is not a restart; different epoch is.
    restarted = OfficeSync(state, {'default': str(root)})
    restarted.epoch = 'new-process'
    assert restarted.exchange('default', 'doc', dict(action='owner-status', owner='browser'))['ownership'] == 'external'


def test_external_change_pauses_preserves_incoming_and_attempt(tmp_path):
    root = tmp_path / 'shared'; root.mkdir()
    sync = OfficeSync(tmp_path / 'state', {'default': str(root)})
    sync.exchange('default', 'doc', dict(action='publish', extension='docx', bytes=office(), base=None))
    def call(action, **kw):
        return sync.exchange('default', 'doc', dict(action=action, owner='browser', **kw))
    r = call('resume'); call('accept', hash=r['hash'], offer_id=r['offer_id'], native_hash='native')
    (root / 'doc.docx').write_bytes(base64.b64decode(office('unexpected')))
    result = call('owner-publish', connection_grant=r['offer_id'], base=r['hash'], bytes=office('pending-local'))
    assert result['ownership'] == 'external'
    assert (root / 'doc.docx').read_bytes() == base64.b64decode(office('unexpected'))
    copies = list((tmp_path / 'state/default/office-backups/doc').glob('*.docx'))
    assert base64.b64decode(office('pending-local')) in [p.read_bytes() for p in copies]
    assert base64.b64decode(office('unexpected')) in [p.read_bytes() for p in copies]
