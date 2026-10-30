import base64
import io
import zipfile
import pytest
from api.cowork_sync import OfficeSync
from api.cowork import Conflict


def office(text='one'):
    b = io.BytesIO()
    with zipfile.ZipFile(b, 'w') as z:
        z.writestr('[Content_Types].xml', '<Types/>')
        z.writestr('word/document.xml', '<document>'+text+'</document>')
    return base64.b64encode(b.getvalue()).decode()


def test_explicit_root_and_stable_roundtrip(tmp_path):
    root = tmp_path / 'shared'; root.mkdir()
    s = OfficeSync(tmp_path / 'state', {'default': str(root)})
    first = s.exchange('default', 'doc', {'action':'publish', 'extension':'docx', 'bytes':office(), 'base':None})
    assert first['state'] == 'synced'
    assert s.exchange('default','doc', {'action':'poll'})['state'] == 'synced'
    (root/'doc.docx').write_bytes(base64.b64decode(office('external')))
    assert s.exchange('default','doc', {'action':'poll'})['state'] == 'settling'
    changed = s.exchange('default','doc', {'action':'poll'})
    assert changed['state'] == 'external'
    with pytest.raises(Conflict):
        s.exchange('default','doc', {'action':'publish','extension':'docx','bytes':office('local'),'base':first['hash']})
    assert s.exchange('default','doc', {'action':'accept','hash':changed['hash'],'offer_id':changed['offer_id']})['state'] == 'synced'
    assert list((tmp_path/'state'/'default'/'office-backups'/'doc').iterdir())
    (root/'doc.docx').unlink()
    assert s.exchange('default','doc',{'action':'poll'})['state']=='offline'
    root.rmdir()
    assert s.exchange('default','doc',{'action':'poll'})['state']=='offline'
    assert OfficeSync(tmp_path/'state',{}).exchange('other','doc',{'action':'poll'})['state']=='disabled'


def test_no_arbitrary_paths_symlinks_or_invalid_office(tmp_path):
    root=tmp_path/'shared';root.mkdir()
    s=OfficeSync(tmp_path/'state',{'default':str(root)})
    with pytest.raises(ValueError):
        s.exchange('default','../bad',{'action':'poll'})
    with pytest.raises(ValueError):
        s.exchange('default','doc',{'action':'publish','extension':'docx','bytes':base64.b64encode(b'bad').decode(),'base':None})
    (root/'doc.docx').symlink_to(tmp_path/'outside')
    with pytest.raises(ValueError):
        s.exchange('default','doc',{'action':'publish','extension':'docx','bytes':office(),'base':None})
