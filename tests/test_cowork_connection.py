import base64
import io
import zipfile
import pytest
import sys
pytestmark = pytest.mark.skipif(sys.platform != 'darwin', reason='real macOS native coordination required')
from api.cowork_sync import OfficeSync, LEASE_SECONDS
from api.cowork import Conflict


def payload(text='one'):
    b = io.BytesIO()
    with zipfile.ZipFile(b, 'w') as z:
        z.writestr(zipfile.ZipInfo('[Content_Types].xml'), '<Types/>')
        z.writestr(zipfile.ZipInfo('word/document.xml'), '<document>' + text + '</document>')
    return base64.b64encode(b.getvalue()).decode()


def test_expired_connection_cannot_write_or_reuse_old_reconciliation(tmp_path, monkeypatch):
    root = tmp_path / 'root'; root.mkdir()
    sync = OfficeSync(tmp_path / 'state', {'default': str(root)})
    sync.exchange('default', 'doc', dict(action='publish', extension='docx', bytes=payload(), base=None))
    def call(action, **kw):
        return sync.exchange('default', 'doc', dict(action=action, owner='browser', **kw))
    r = call('resume'); call('accept', hash=r['hash'], offer_id=r['offer_id'], native_hash='native')
    grant = sync.assert_writable('default', 'doc', 'browser')
    import api.cowork_sync as module
    now = module.time.monotonic()
    monkeypatch.setattr(module.time, 'monotonic', lambda: now + LEASE_SECONDS + 1)
    with pytest.raises(Conflict):
        sync.assert_writable('default', 'doc', 'browser')
    with pytest.raises(Conflict):
        call('owner-publish', base=r['hash'], bytes=payload('stale-ai'))
    # Old ack must not revive an expired connection after a fresh status.
    call('accept', hash=r['hash'], offer_id=r['offer_id'], native_hash='native')
    with pytest.raises(Conflict):
        sync.assert_writable('default', 'doc', 'browser')
    fresh = call('resume'); call('accept', hash=fresh['hash'], offer_id=fresh['offer_id'], native_hash='native')
    assert sync.assert_writable('default', 'doc', 'browser') != grant
    with pytest.raises(Conflict):
        call('owner-publish', connection_grant=grant, base=fresh['hash'], bytes=payload('queued-before-loss'))


def test_changed_offered_bytes_reject_native_replacement(tmp_path):
    root = tmp_path / 'root'; root.mkdir()
    sync = OfficeSync(tmp_path / 'state', {'default': str(root)})
    sync.exchange('default', 'doc', dict(action='publish', extension='docx', bytes=payload(), base=None))
    offer = sync.exchange('default', 'doc', dict(action='resume', owner='browser'))
    (root / 'doc.docx').write_bytes(base64.b64decode(payload('later-cloud-arrival')))
    with pytest.raises(Conflict):
        sync.exchange('default', 'doc', dict(action='verify-offer', owner='browser', hash=offer['hash'], offer_id=offer['offer_id']))


def test_backend_inference_cannot_cross_reconnection_grant(tmp_path, monkeypatch):
    import json
    from urllib.parse import urlparse
    import api.config as config
    import api.profiles as profiles
    import api.helpers as helpers
    import api.cowork as cowork
    state = tmp_path / 'state'; state.mkdir()
    root = tmp_path / 'shared'; root.mkdir()
    (state / 'cowork-office-roots.json').write_text(json.dumps({'default': str(root)}))
    monkeypatch.setattr(config, 'STATE_DIR', str(state))
    monkeypatch.setattr(profiles, 'get_active_profile_name', lambda: 'default')
    monkeypatch.setattr(helpers, 'j', lambda handler, data: (200, data))
    monkeypatch.setattr(helpers, 'bad', lambda handler, message, status=400: (status, message))
    store = cowork.SnapshotStore(state / 'cowork')
    store.claim('default', 'doc', 'browser')
    store.save('default', 'doc', 0, 'document', {'type': 'doc'}, owner='browser')
    sync = OfficeSync(state / 'cowork', {'default': str(root)})
    sync.exchange('default', 'doc', dict(action='publish', extension='docx', bytes=payload(), base=None))
    def reconnect():
        offered = sync.exchange('default', 'doc', dict(action='resume', owner='browser'))
        sync.exchange('default', 'doc', dict(action='accept', owner='browser', hash=offered['hash'], offer_id=offered['offer_id'], native_hash='native'))
    reconnect()
    def inference(body, profile):
        sync.exchange('default', 'doc', dict(action='yield', owner='browser'))
        reconnect()
        return {'operations': [{'type': 'stop'}]}
    monkeypatch.setattr(cowork, 'infer_intent', inference)
    body = dict(profile='default', owner='browser', document_id='doc', connection_grant=sync.assert_writable('default', 'doc', 'browser'), utterance_id='phrase', text='Stop', context={})
    status, detail = cowork.handle(None, urlparse('/api/cowork/intent'), body)
    assert status == 409 and 'old intent canceled' in detail
    sync.exchange('default', 'doc', dict(action='yield', owner='browser'))
    status, _ = cowork.handle(None, urlparse('/api/cowork/document'), dict(profile='default', owner='browser', document_id='doc', revision=1, kind='document', snapshot={'stale': True}))
    assert status == 409
    assert store.load('default', 'doc')['snapshot'] == {'type': 'doc'}
