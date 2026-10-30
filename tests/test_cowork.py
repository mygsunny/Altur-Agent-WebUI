"""Synthetic co-work storage and constrained intent boundary tests."""
import importlib
import pytest


def module():
    return importlib.import_module('api.cowork')


def test_atomic_revisions_recovery_and_profile_isolation(tmp_path):
    store = module().SnapshotStore(tmp_path)
    first = store.save('alpha', 'doc-1', 0, 'document', {'type': 'doc', 'content': []})
    assert first['revision'] == 1
    second = store.save('alpha', 'doc-1', 1, 'document', {'type': 'doc', 'content': [{'type': 'paragraph'}]})
    assert second['revision'] == 2
    assert store.load('alpha', 'doc-1')['snapshot'] == second['snapshot']
    assert store.load('alpha', 'doc-1', previous=True) == first
    assert store.load('beta', 'doc-1') is None
    with pytest.raises(module().Conflict):
        store.save('alpha', 'doc-1', 1, 'document', {})
    assert store.load('alpha', 'doc-1') == second


@pytest.mark.parametrize('identity', ['../bad', '', '/tmp/data', 'x/y', 'a'*81])
def test_reject_invalid_identity(tmp_path, identity):
    with pytest.raises(ValueError):
        module().SnapshotStore(tmp_path).save('default', identity, 0, 'document', {})


def test_no_kind_switch_or_invalid_revision(tmp_path):
    store = module().SnapshotStore(tmp_path)
    store.save('default', 'doc', 0, 'document', {})
    with pytest.raises(ValueError):
        store.save('default', 'doc', 1, 'sheet', {})
    with pytest.raises(ValueError):
        store.save('default', 'new', True, 'document', {})


def test_storage_closes_every_connection(tmp_path, monkeypatch):
    import sqlite3
    real_connect = sqlite3.connect
    connections = []
    class Tracked(sqlite3.Connection):
        closed = False
        def close(self):
            self.closed = True
            super().close()
    def connect(*args, **kwargs):
        conn = real_connect(*args, **kwargs, factory=Tracked)
        connections.append(conn)
        return conn
    monkeypatch.setattr(sqlite3, 'connect', connect)
    store = module().SnapshotStore(tmp_path)
    store.save('default', 'doc', 0, 'document', {})
    store.load('default', 'doc')
    assert connections and all(conn.closed for conn in connections)


def test_server_lease_refuses_other_browser_and_stale_owner(tmp_path):
    import time
    m = module()
    store = m.SnapshotStore(tmp_path)
    store.claim('default', 'doc', 'owner1')
    with pytest.raises(m.Conflict):
        store.claim('default', 'doc', 'owner2')
    with pytest.raises(m.Conflict):
        store.save('default', 'doc', 0, 'document', {}, owner='owner2')
    store.save('default', 'doc', 0, 'document', {}, owner='owner1')
    store.claim('default', 'doc', 'owner2', now=time.time()+31)
    with pytest.raises(m.Conflict):
        store.save('default', 'doc', 1, 'document', {}, owner='owner1')


def test_intent_schema_denies_code_and_foreign_identity():
    m = module()
    assert m.validate_intent({'document_id':'d', 'utterance_id':'u', 'operations':[{'type':'undo'}]}, 'd', 'u')['operations'][0]['type'] == 'undo'
    for payload in [
        {'document_id':'other','utterance_id':'u','operations':[{'type':'undo'}]},
        {'document_id':'d','utterance_id':'u','operations':[{'type':'javascript','code':'alert(1)'}]},
        {'document_id':'d','utterance_id':'u','operations':[{'type':'sheet.set','range':'A0','values':[[1]]}]},
        {'document_id':'d','utterance_id':'u','operations':[{'type':'document.replace','find':'','text':'oops'}]},
    ]:
        with pytest.raises(ValueError):
            m.validate_intent(payload, 'd', 'u')
