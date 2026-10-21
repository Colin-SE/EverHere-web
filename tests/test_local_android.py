"""安卓真实合成归档、原图、冲突副本和云端授权边界。"""
import copy
import hashlib
import json
from io import BytesIO
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile

import pytest
from sqlalchemy import select

from app.extensions import db
from app.models import ArchiveJob, CloudConnection, LifeRecord
from app.security import APIError
from conftest import Client
from sync_contract import android_json, event_date, int64, parse_archive

FIXTURES=Path(__file__).parent/'fixtures'


def source(app):
    app.config['CLOUD_REGION']='global'
    return json.loads((FIXTURES/'android-native-v1.json').read_text(encoding='utf-8'))


def checksum(archive):
    data=android_json(archive['data']);archive['manifest']['dataBytes']=str(len(data));archive['manifest']['dataSha256']=hashlib.sha256(data).hexdigest()


def preview_file(client,raw,filename='data.json'):
    return client.client.post('/api/v1/archive/files/preview',data={'archive':(BytesIO(raw),filename)},headers={'X-CSRF-Token':client.token})


def confirm(client,job,**options):
    return client.call('POST','/archive/jobs/'+job+'/confirm',{'confirmed':True,**options})


def test_actual_android_json_roundtrip_and_edit_preserve_raw_fields(app,client):
    archive=source(app)
    preview=preview_file(client,json.dumps(archive).encode());assert preview.status_code==200,preview.json
    job=preview.json['data']['id'];assert confirm(client,job).status_code==400
    assert confirm(client,job,acceptMissingPhotos=True).status_code==200
    before=client.call('GET','/archive/export').json['data']
    assert {d['id']:d for d in before['data']['documents']}=={d['id']:d for d in archive['data']['documents']}
    record=client.call('GET','/records').json['data']['records'][0]
    assert record['eventDate']=='1960-02' and record['tags']==['archive','archive'] and record['latitude']==0
    result=client.call('PUT','/records/'+record['id'],{**record,'title':'Web 同 ID 编辑'})
    assert result.status_code==200,result.json
    doc=next(d for d in client.call('GET','/archive/export').json['data']['data']['documents'] if d['id']==record['id'])
    original=archive['data']['documents'][-1]
    assert doc['id']==original['id'] and doc['title']=='Web 同 ID 编辑'
    for key in ['createdAt','eventDate','timezone','coordinates','tags','entityIds','photos']:
        assert doc[key]==original[key]
    assert client.call('GET','/records?trash=true').json['data']['total']==1
    assert client.call('GET','/archive/export.zip').json['error']['code']=='original_missing'


def test_actual_android_zip_restores_original_bytes_and_exports_valid_zip(app,client):
    app.config['CLOUD_REGION']='global'
    raw=(FIXTURES/'android-native-v1.zip').read_bytes()
    response=preview_file(client,raw,'native.zip');assert response.status_code==200,response.json
    job=response.json['data']['id'];assert confirm(client,job).status_code==200
    assert confirm(client,job).json['data']['replayed'] is True
    record=client.call('GET','/records').json['data']['records'][0]
    original=source(app)['data']['documents'][-1]
    for uri,photo in zip(record['photoUris'],original['photos']):
        result=client.client.get(uri);assert result.status_code==200
        assert hashlib.sha256(result.data).hexdigest()==photo['sha256']
    exported=client.call('GET','/archive/export.zip');assert exported.status_code==200,exported.json
    with ZipFile(BytesIO(exported.data)) as zipped:
        info=json.loads(zipped.read('manifest.json'));data_bytes=zipped.read('data.json');data=json.loads(data_bytes)
        assert info['complete'] and info['missingOriginals']==[]
        parsed=parse_archive({'format':'everhere-archive','archiveVersion':1,'manifest':info,'data':data},'global',kind='zip',data_bytes=data_bytes)
        assert len(parsed['documents'])==3 and len(info['assets'])==2
    other=Client(app);assert other.call('GET','/archive/jobs/'+job).status_code==404


def test_import_conflicts_copy_deterministically_without_overwrite(app,client):
    archive=source(app);raw=json.dumps(archive).encode()
    first=preview_file(client,raw).json['data'];assert confirm(client,first['id'],acceptMissingPhotos=True).status_code==200
    changed=copy.deepcopy(archive);changed['data']['documents'][-1]['content']='来自另一个端的内容';checksum(changed)
    raw=json.dumps(changed).encode();second=preview_file(client,raw).json['data'];assert len(second['conflicts'])==1
    assert confirm(client,second['id'],acceptMissingPhotos=True).status_code==409
    assert confirm(client,second['id'],acceptMissingPhotos=True,copyConflicts=True).status_code==200
    records=client.call('GET','/records').json['data']['records'];assert len(records)==2
    assert {r['content'] for r in records}=={'Offline portable archive','来自另一个端的内容'}
    before={r['id'] for r in records}
    third=preview_file(client,raw).json['data'];assert confirm(client,third['id'],acceptMissingPhotos=True,copyConflicts=True).status_code==200
    assert {r['id'] for r in client.call('GET','/records').json['data']['records']}==before


def test_import_preview_rechecks_target_and_occupying_draft(app,client):
    raw=json.dumps(source(app)).encode();job=preview_file(client,raw).json['data']
    client.create()
    assert confirm(client,job['id'],acceptMissingPhotos=True).json['error']['code']=='import_changed'
    assert client.call('POST','/archive/jobs/'+job['id']+'/refresh',{}).status_code==200
    assert confirm(client,job['id'],acceptMissingPhotos=True).status_code==200
    record=next(r for r in client.call('GET','/records').json['data']['records'] if r['datePrecision']=='month')
    draft=client.call('POST','/drafts',{'recordId':record['id']}).json['data']
    preview=preview_file(client,raw).json['data'];assert any(p['id']==record['id'] for p in preview['conflicts'])
    assert confirm(client,preview['id'],acceptMissingPhotos=True,copyConflicts=True).status_code==200
    assert client.call('GET','/drafts/'+draft['id']).status_code==200


@pytest.mark.parametrize('change',['checksum','region','protected','unknown','manifest'])
def test_bad_native_archives_reject_atomically(app,client,change):
    archive=source(app)
    if change=='checksum':archive['data']['documents'][-1]['content']='被改动'
    if change=='region':archive['manifest']['region']='cn'
    if change=='protected':archive['data']['documents'][-1]['privacy']='vault';checksum(archive)
    if change=='unknown':archive['data']['documents'][-1]['unknown']='value';checksum(archive)
    if change=='manifest':archive['manifest']['counts']['record']=999
    response=preview_file(client,json.dumps(archive).encode());assert response.status_code==400,response.json
    assert client.call('GET','/records').json['data']['total']==0


def test_zip_traversal_duplicate_and_changed_original_reject(app,client):
    app.config['CLOUD_REGION']='global';raw=(FIXTURES/'android-native-v1.zip').read_bytes()
    for mode in ['traversal','duplicate','photo']:
        output=BytesIO()
        with ZipFile(BytesIO(raw)) as source_zip,ZipFile(output,'w') as target:
            for index,item in enumerate(source_zip.infolist()):
                content=source_zip.read(item.filename)
                target.writestr(item.filename,b'broken' if mode=='photo' and index==2 else content)
            if mode=='traversal':target.writestr('../outside.txt',b'bad')
            if mode=='duplicate':
                import warnings
                with warnings.catch_warnings():warnings.simplefilter('ignore',UserWarning);target.writestr('data.json',b'{}')
        assert preview_file(client,output.getvalue(),'bad.zip').status_code==400
    assert client.call('GET','/records').json['data']['total']==0


def test_stage_is_encrypted_and_explicit_discard_removes_it(app,client):
    response=preview_file(client,json.dumps(source(app)).encode());job=response.json['data']['id']
    path=Path(app.config['ARCHIVE_STAGE_DIRECTORY'])/(job+'.bin')
    assert path.exists() and b'Offline portable archive' not in path.read_bytes()
    assert client.call('DELETE','/archive/jobs/'+job,{}).status_code==200
    assert not path.exists() and client.call('GET','/archive/jobs/'+job).status_code==404


@pytest.mark.parametrize('value',['9223372036854775807','-9223372036854775808','9007199254740993'])
def test_int64_preserved_as_decimal_text(value):assert int64(value)==value


@pytest.mark.parametrize('value',['-0','01','9223372036854775808',9007199254740993])
def test_lossy_integer_rejected(value):
    with pytest.raises(APIError):int64(value)


def test_cloud_login_only_calls_auth_and_does_not_upload(app,client,monkeypatch):
    from app.api import cloud
    account=str(uuid4());calls=[]
    def remote(path,data=None,token=None):
        calls.append(path);return {'region':'cn','userId':account,'email':'cloud@example.com','accessToken':'access'}
    monkeypatch.setattr(cloud,'remote',remote)
    app.config['CLOUD_API_URL']='http://127.0.0.1:3001'
    client.create()
    response=client.call('POST','/cloud/login',{'email':'cloud@example.com','password':'secret'})
    assert response.status_code==200 and calls==['/v1/auth/login']
    assert client.call('GET','/records').json['data']['total']==1
    assert 'token' not in json.dumps(response.json).lower()


def test_client_flag_cannot_grant_entitlement_or_scoped_sync(app,client,monkeypatch):
    from app.api import cloud
    account=str(uuid4())
    with client.client.session_transaction() as session:owner=session['space_id']
    with app.app_context():db.session.add(CloudConnection(id=owner,account_id=account,email='test@example.com',token='secret',region='cn',enabled=True));db.session.commit()
    def unavailable(*args,**kwargs):raise APIError('权益接口未提供',503,'cloud_capability_unavailable')
    monkeypatch.setattr(cloud,'remote',unavailable)
    assert client.call('GET','/cloud/status').json['data']['enabled'] is False
    assert client.call('POST','/cloud/consent',{'enabled':True,'isVip':True}).status_code==503
    monkeypatch.setattr(cloud,'remote',lambda *a,**k:{'region':'cn','userId':account,'cloudSync':{'active':True,'expiresAt':'2099-01-01T00:00:00Z'}})
    assert client.call('POST','/cloud/consent',{'enabled':True}).json['error']['code']=='scoped_sync_unavailable'
