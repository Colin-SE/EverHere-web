"""按安卓当前行为验证本机事实、日期查询、草稿、人物与回收站。"""
from io import BytesIO

import pytest
from PIL import Image
from sqlalchemy import inspect, select

from app.extensions import db
from app.models import Draft, LifeRecord, Photo
from conftest import Client


def picture(color='green'):
    output=BytesIO();Image.new('RGB',(30,20),color).save(output,'PNG');output.seek(0);return output


def test_default_local_space_headers_and_removed_features(app,client):
    assert client.client.get('/').status_code==200
    assert 'no-store' in client.client.get('/').headers['Cache-Control']
    assert client.call('GET','/auth/session').json['data']['user'] is None
    for method,path in [('POST','/auth/register'),('POST','/auth/login'),('POST','/auth/vault'),('DELETE','/auth/account')]:
        assert client.call(method,path,{}).status_code==404
    assert client.create(isPrivate=True).status_code==400
    assert client.call('POST','/drafts',{'values':{'title':'不能降级保存','privacy':'vault'}}).status_code==400
    assert client.client.post('/api/v1/records',json={'title':'CSRF'}).status_code==403
    with app.app_context():assert 'users' not in inspect(db.engine).get_table_names()


def test_spaces_do_not_leak_records_photos_or_relationships(app,client):
    record=client.create().json['data'];node=client.call('POST','/graph/entities',{'name':'同名人物','summary':'甲'}).json['data']
    other=Client(app)
    assert other.call('GET','/records').json['data']['total']==0
    assert other.call('GET','/records/'+record['id']).status_code==404
    assert other.create(linkedEntityIds=[node['id']]).status_code==400
    assert other.call('DELETE','/graph/entities/'+node['id'],{}).status_code==404


@pytest.mark.parametrize('changes',[
 {'title':'','content':'   '},{'eventDate':'2026-02-30'},{'datePrecision':{}},{'latitude':True,'longitude':1},
 {'latitude':91,'longitude':0},{'latitude':0},{'tags':'标签'},{'completionState':3},{'recordState':[]},
 {'photoUris':['https://example.com/image.png']},{'linkedEntityIds':['missing']},{'datePrecision':'month','eventDate':'2026-10-01'},
 {'datePrecision':'unknown','eventDate':'2026-10-01'},{'datePrecision':'range','eventDate':'2026-10-01','eventEndAt':'2026-09-30'},
])
def test_record_validation_preserves_failed_input(client,changes):
    assert client.create(**changes).status_code==400
    assert client.call('GET','/records').json['data']['total']==0


@pytest.mark.parametrize('precision,start,end',[
 ('unknown',None,None),('year','1960',None),('year','-0000001960',None),('month','1960-02',None),
 ('day','2024-02-29',None),('range','2026-09-30','2026-10-20')])
def test_dates_preserve_exact_precision_and_raw_text(client,precision,start,end):
    result=client.create(datePrecision=precision,eventDate=start,eventEndAt=end,timezone='GMT')
    assert result.status_code==201,result.json
    value=result.json['data'];assert value['eventDate']==start and value['eventEndAt']==end and value['datePrecision']==precision and value['timezone']=='GMT'


def test_query_targets_words_progress_and_date_overlap(client):
    client.create(title='隐藏时间轴',showInTimeline=False,datePrecision='year',eventDate='2026')
    client.create(title='杭州散步',content='雨后',tags=['朋友','朋友'],mood='平静',latitude=0,longitude=0,showOnGlobe=True,datePrecision='month',eventDate='2026-10',completionState='started')
    client.create(title='跨月旅程',datePrecision='range',eventDate='2026-09-28',eventEndAt='2026-10-02')
    client.create(title='未知日期',eventDate=None,datePrecision='unknown')
    assert client.call('GET','/records?target=all').json['data']['total']==4
    assert client.call('GET','/records?target=timeline').json['data']['total']==3
    assert client.call('GET','/records?target=spatial').json['data']['total']==1
    assert client.call('GET','/records?q=雨后%20朋友%20平静').json['data']['total']==1
    assert client.call('GET','/records?from=2026-10-01&to=2026-10-01').json['data']['total']==3
    assert client.call('GET','/records?precision=month&progress=unfinished').json['data']['total']==1
    assert client.call('GET','/records?q=%25').json['data']['total']==0


def test_plan_to_fact_requires_actual_date_but_progress_is_independent(client):
    record=client.create(recordState='planned',completionState='cancelled').json['data']
    assert client.call('PUT','/records/'+record['id'],{**record,'recordState':'occurred'}).json['error']['code']=='actual_date_required'
    result=client.call('PUT','/records/'+record['id'],{**record,'recordState':'occurred','actualDateConfirmed':True})
    assert result.status_code==200 and result.json['data']['completionState']=='cancelled'
    assert client.call('PUT','/records/'+record['id'],record).status_code==409


def test_soft_delete_restores_original_id_relations_and_photos(client):
    photo=client.client.post('/api/v1/photos',data={'photo':(picture(),'image.png')},headers={'X-CSRF-Token':client.token}).json['data']['uri']
    person=client.call('POST','/graph/entities',{'name':'朋友'}).json['data']
    record=client.create(photoUris=[photo],linkedEntityIds=[person['id']]).json['data']
    deleted=client.call('DELETE','/records/'+record['id'],{'version':record['version']})
    assert deleted.status_code==200 and deleted.json['data']['recoverable']
    assert client.call('GET','/records/'+record['id']).status_code==404
    assert client.call('GET','/records').json['data']['total']==0
    trash=client.call('GET','/records?trash=true').json['data']['records'][0]
    assert client.client.get(photo).status_code==200
    restored=client.call('POST','/records/'+record['id']+'/restore',{'version':trash['version']}).json['data']
    assert restored['id']==record['id'] and restored['linkedEntityIds']==[person['id']] and restored['photoUris']==[photo]


def test_photo_original_bytes_and_failed_batch_are_atomic(app,client):
    original=picture().getvalue()
    response=client.client.post('/api/v1/photos',data={'photo':(BytesIO(original),'a.png')},headers={'X-CSRF-Token':client.token})
    uri=response.json['data']['uri'];assert client.client.get(uri).data==original and client.client.get(uri).mimetype=='image/png'
    before=None
    with app.app_context():before=len(list(db.session.scalars(select(Photo))))
    result=client.client.post('/api/v1/photos/batch',data={'photos':[(picture(),'valid.png'),(BytesIO(b'broken'),'bad.png')]},headers={'X-CSRF-Token':client.token})
    assert result.status_code==400
    with app.app_context():assert len(list(db.session.scalars(select(Photo))))==before


def test_draft_raw_values_restart_conflict_and_commit_receipt(app,client):
    draft=client.call('POST','/drafts',{'kind':'record','values':{'title':'尚未完成','datePrecision':'day','eventDate':'坏日期','latitude':'x'}}).json['data']
    assert client.call('GET','/records').json['data']['total']==0
    assert client.call('GET','/drafts/'+draft['id']).json['data']['values']['eventDate']=='坏日期'
    assert client.call('POST','/drafts/'+draft['id']+'/commit',{'version':draft['version']}).status_code==400
    value={'title':'草稿完成','content':'正文\n不修剪结尾\n','datePrecision':'unknown','eventDate':'','latitude':'','longitude':'','completionState':'started'}
    draft=client.call('PUT','/drafts/'+draft['id'],{'version':draft['version'],'values':value}).json['data']
    assert client.call('PUT','/drafts/'+draft['id'],{'version':1,'values':{'title':'旧标签'}}).status_code==409
    first=client.call('POST','/drafts/'+draft['id']+'/commit',{'version':draft['version']}).json['data']
    second=client.call('POST','/drafts/'+draft['id']+'/commit',{'version':draft['version']}).json['data']
    assert first['id']==second['id'] and second['replayed']
    record=client.call('GET','/records/'+first['id']).json['data'];assert record['content']==value['content'] and record['completionState']=='started'
    client.call('DELETE','/records/'+first['id'],{'version':record['version']})
    client.call('POST','/drafts/'+draft['id']+'/commit',{'version':draft['version']})
    assert client.call('GET','/records').json['data']['total']==0
    assert client.call('GET','/drafts').json['data']['drafts']==[]
    assert Client(app).call('GET','/drafts/'+draft['id']).status_code==404


def test_formal_change_does_not_allow_old_draft_to_overwrite(client):
    record=client.create().json['data'];draft=client.call('POST','/drafts',{'recordId':record['id']}).json['data']
    assert client.call('PUT','/records/'+record['id'],{**record,'title':'另一标签的新输入'}).status_code==200
    assert client.call('POST','/drafts/'+draft['id']+'/commit',{'version':draft['version']}).status_code==409
    assert client.call('GET','/drafts/'+draft['id']).status_code==200
    assert client.call('GET','/records/'+record['id']).json['data']['title']=='另一标签的新输入'


def test_people_drafts_same_names_and_unlink_preserve_record(client):
    ids=[]
    for meaning in ['  一起读书\n','另一位朋友']:
        draft=client.call('POST','/drafts',{'kind':'person','values':{'name':'同名','summary':meaning}}).json['data']
        value=client.call('POST','/drafts/'+draft['id']+'/commit',{'version':draft['version']})
        assert value.status_code==200,value.json
        ids.append(value.json['data']['id'])
    assert ids[0]!=ids[1]
    people=client.call('GET','/graph').json['data']['entities'];assert len(people)==2
    person=next(p for p in people if p['id']==ids[0]);assert person['summary']=='  一起读书\n'
    assert client.call('PUT','/graph/entities/'+ids[0],{'name':'过期输入'}).status_code==409
    record=client.create(linkedEntityIds=[ids[0],ids[1]]).json['data']
    assert client.call('DELETE','/graph/entities/'+ids[0],{'version':person['version']}).status_code==200
    record=client.call('GET','/records/'+record['id']).json['data'];assert record['linkedEntityIds']==[ids[1]] and record['content']=='正文'
    assert len(client.call('GET','/graph').json['data']['entities'])==1


def test_empty_database_migration_matches_current_models():
    from app import create_app
    application=create_app({'SQLALCHEMY_DATABASE_URI':'sqlite://'})
    runner=application.test_cli_runner();result=runner.invoke(args=['db','upgrade']);assert result.exit_code==0,result.output
    checked=runner.invoke(args=['db','check']);assert checked.exit_code==0,checked.output
    with application.app_context():assert 'users' not in inspect(db.engine).get_table_names();db.engine.dispose()
