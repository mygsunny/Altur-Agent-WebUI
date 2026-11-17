import base64
import os
import pytest
from api.cowork_sync import OfficeSync
from tests.test_cowork_sync import office


def test_publish_never_replaces_noncooperative_writer(tmp_path, monkeypatch):
    root = tmp_path / 'shared'; root.mkdir()
    sync = OfficeSync(tmp_path / 'state', {'default': str(root)})
    first = sync.exchange('default', 'doc', dict(action='publish', extension='docx', bytes=office(), base=None))
    external = base64.b64decode(office('external rename at publication'))
    original_link, original_replace = os.link, os.replace
    raced = False
    def external_rename():
        nonlocal raced
        raced = True
        incoming = root / 'incoming'
        incoming.write_bytes(external)
        original_replace(incoming, root / 'doc.docx')
    def racing_link(src, dst, **kwargs):
        if str(src).startswith('.cowork-'):
            external_rename()
        return original_link(src, dst, **kwargs)
    def racing_replace(src, dst, **kwargs):
        if dst == 'doc.docx' and str(src).startswith('.cowork-'):
            external_rename()
        return original_replace(src, dst, **kwargs)
    monkeypatch.setattr(os, 'link', racing_link)
    monkeypatch.setattr(os, 'replace', racing_replace)
    result = sync.exchange('default', 'doc', dict(action='publish', extension='docx', bytes=office('local'), base=first['hash']))
    assert raced
    assert (root / 'doc.docx').read_bytes() == external
    assert result['filename'] != 'doc.docx'
    assert (root / result['filename']).read_bytes() == base64.b64decode(office('local'))


def test_accept_retry_after_external_rename_is_idempotent(tmp_path):
    root=tmp_path/'shared'; root.mkdir()
    sync=OfficeSync(tmp_path/'state', {'default':str(root)})
    sync.exchange('default','doc',dict(action='publish',extension='docx',bytes=office(),base=None))
    (root/'doc.docx').write_bytes(base64.b64decode(office('offered')))
    sync.exchange('default','doc',dict(action='poll'))
    offered=sync.exchange('default','doc',dict(action='poll'))
    (root/'doc.docx').write_bytes(base64.b64decode(office('later')))
    request=dict(action='accept',hash=offered['hash'],offer_id=offered['offer_id'],native_hash='normalized')
    assert sync.exchange('default','doc',request)['state']=='synced'
    assert sync.exchange('default','doc',request)['state']=='synced'
    assert sync.exchange('default','doc',dict(action='poll'))['state']=='settling'
    assert sync.exchange('default','doc',dict(action='poll'))['state']=='external'


def test_native_import_receipt_is_atomic_and_idempotent(tmp_path):
    from api.cowork import SnapshotStore
    store=SnapshotStore(tmp_path/'state')
    original=store.save('default','doc',0,'document',{'type':'doc'})
    receipt={'hash':'a'*64,'native_hash':'b'*64,'offer_id':'c'*32}
    imported={'type':'doc','content':[{'type':'paragraph'}]}
    result=store.save('default','doc',original['revision'],'document',imported,office_import=receipt)
    assert result['office_import']==receipt
    assert store.save('default','doc',original['revision'],'document',imported,office_import=receipt)==result
    assert store.load('default','doc',previous=True)==original
    assert store.load('default','doc')['office_import']==receipt


def test_database_symlink_refused(tmp_path):
    root = tmp_path / 'shared'; root.mkdir()
    state = tmp_path / 'state' / 'default'; state.mkdir(parents=True)
    outside = tmp_path / 'outside'; outside.write_bytes(b'untouched')
    (state / 'office-sync.sqlite3').symlink_to(outside)
    with pytest.raises(ValueError):
        OfficeSync(tmp_path / 'state', {'default': str(root)}).exchange('default', 'doc', dict(action='publish', extension='docx', bytes=office(), base=None))
    assert outside.read_bytes() == b'untouched'


def test_same_hash_returning_later_gets_fresh_offer_and_old_ack_cannot_rewind(tmp_path):
    shared=tmp_path/'shared';shared.mkdir()
    sync=OfficeSync(tmp_path/'state',{'default':str(shared)})
    sync.exchange('default','doc',dict(action='publish',extension='docx',bytes=office(),base=None))
    a=base64.b64decode(office('A'));b=base64.b64decode(office('B'))
    def offer(data):
        (shared/'doc.docx').write_bytes(data)
        sync.exchange('default','doc',dict(action='poll'))
        return sync.exchange('default','doc',dict(action='poll'))
    def accept(r):return sync.exchange('default','doc',dict(action='accept',hash=r['hash'],offer_id=r['offer_id'],native_hash='n'))
    first=offer(a);accept(first)
    second=offer(b);accept(second)
    accept(first)
    assert sync.exchange('default','doc',dict(action='poll'))['hash']==second['hash']
    again=offer(a);assert again['offer_id']!=first['offer_id'];accept(again)
    assert sync.exchange('default','doc',dict(action='poll'))['state']=='synced'
