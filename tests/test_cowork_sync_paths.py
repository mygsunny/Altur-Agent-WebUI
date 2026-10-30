import base64
import os
import stat
import pytest
from api.cowork import SnapshotStore
from api.cowork_sync import OfficeSync, private_backup
from tests.test_cowork_sync import office

@pytest.mark.parametrize('name',['office-sync.sqlite3','snapshots.sqlite3','office-sync.sqlite3.lock','snapshots.sqlite3.lock','office-sync.sqlite3-wal','snapshots.sqlite3-journal'])
def test_private_storage_symlinks_cannot_touch_outside(tmp_path,name):
    shared=tmp_path/'shared';shared.mkdir()
    state=tmp_path/'state'/'default';state.mkdir(parents=True)
    outside=tmp_path/'outside';outside.write_bytes(b'untouched')
    (state/name).symlink_to(outside)
    with pytest.raises(ValueError):
        if name.startswith('snapshots'):
            SnapshotStore(tmp_path/'state').load('default','doc')
        else:
            OfficeSync(tmp_path/'state',{'default':str(shared)}).exchange('default','doc',dict(action='publish',extension='docx',bytes=office(),base=None))
    assert outside.read_bytes()==b'untouched'

@pytest.mark.parametrize('tree',['office-backups','native-backups'])
def test_backup_symlink_and_hardlink_refused(tmp_path,tree):
    state=tmp_path/'state';profile=state/'default';profile.mkdir(parents=True)
    outside=tmp_path/'outside';outside.mkdir()
    (profile/tree).symlink_to(outside,target_is_directory=True)
    with pytest.raises((ValueError,OSError)):
        private_backup(state,'default',tree,'doc',b'snapshot','json')
    assert list(outside.iterdir())==[]


def test_descriptor_walk_refuses_ancestor_swapped_to_symlink(tmp_path,monkeypatch):
    parent=tmp_path/'parent';shared=parent/'shared';shared.mkdir(parents=True)
    outside=tmp_path/'outside';(outside/'shared').mkdir(parents=True)
    sentinel=outside/'shared'/'doc.docx';sentinel.write_bytes(b'untouched')
    original=os.open;swapped=False
    def race(name,flags,*args,**kwargs):
        nonlocal swapped
        if name=='parent' and kwargs.get('dir_fd') is not None and not swapped:
            swapped=True;parent.rename(tmp_path/'detached');parent.symlink_to(outside,target_is_directory=True)
        return original(name,flags,*args,**kwargs)
    monkeypatch.setattr(os,'open',race)
    result=OfficeSync(tmp_path/'state',{'default':str(shared)}).exchange('default','doc',dict(action='publish',extension='docx',bytes=office(),base=None))
    assert swapped and result['state']=='offline'
    assert sentinel.read_bytes()==b'untouched'


def test_private_database_and_backups_permissions(tmp_path):
    shared=tmp_path/'shared';shared.mkdir()
    OfficeSync(tmp_path/'state',{'default':str(shared)}).exchange('default','doc',dict(action='publish',extension='docx',bytes=office(),base=None))
    SnapshotStore(tmp_path/'state').save('default','doc',0,'document',{'type':'doc'})
    for path in (tmp_path/'state').rglob('*'):
        assert stat.S_IMODE(path.stat().st_mode)==(0o700 if path.is_dir() else 0o600)

@pytest.mark.parametrize('tree',['office-backups','native-backups'])
def test_backup_content_addressed_hardlink_refused(tmp_path,tree):
    import hashlib
    state=tmp_path/'state';dest=state/'default'/tree/'doc';dest.mkdir(parents=True)
    outside=tmp_path/'outside';outside.write_bytes(b'snapshot')
    os.link(outside,dest/(hashlib.sha256(b'snapshot').hexdigest()+'.json'))
    with pytest.raises(ValueError):
        private_backup(state,'default',tree,'doc',b'snapshot','json')
    assert outside.read_bytes()==b'snapshot'

@pytest.mark.parametrize('name',['office-sync.sqlite3','snapshots.sqlite3'])
def test_database_hardlink_refused(tmp_path,name):
    state=tmp_path/'state';folder=state/'default';folder.mkdir(parents=True)
    outside=tmp_path/'outside';outside.write_bytes(b'untouched')
    os.link(outside,folder/name)
    from api.cowork_sync import private_database
    with pytest.raises(ValueError):
        with private_database(folder,name):pass
    assert outside.read_bytes()==b'untouched'
