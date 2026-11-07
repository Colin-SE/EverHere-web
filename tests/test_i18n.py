"""语言仅影响显示，资料、归属、区域和归档事实必须保持不变。"""
import json
from pathlib import Path


def test_page_language_cookie_and_unsupported_value(client):
    assert '<html lang="zh-CN">' in client.client.get('/').text
    client.client.set_cookie('everhere-language', 'en')
    page = client.client.get('/')
    assert '<html lang="en">' in page.text and 'New life record' in page.text
    assert 'value="开心">Happy</option>' in page.text
    assert page.headers['Content-Language'] == 'en'
    assert client.client.get('/login').location.endswith('/workspace#account')
    client.client.set_cookie('everhere-language', '../global')
    assert '<html lang="zh-CN">' in client.client.get('/').text


def test_language_keeps_records_owner_and_session(client):
    person = client.call('POST', '/graph/entities', {'name': '人物', 'summary': '我的生活'}).json['data']
    saved = client.create(title='人生记录', content='中文原文 & English', mood='开心', placeName='地点', tags=['我的'], linkedEntityIds=[person['id']]).json['data']
    session = client.call('GET', '/auth/session').json['data']
    client.client.set_cookie('everhere-language', 'en')
    assert client.call('GET', '/records/'+saved['id']).json['data'] == saved
    people = client.call('GET', '/graph').json['data']['entities']
    assert next(row for row in people if row['id'] == person['id'])['name'] == '人物'
    assert client.call('GET', '/auth/session').json['data'] == session


def test_english_api_validation_and_csrf_keep_codes_and_status(client):
    client.client.set_cookie('everhere-language', 'en')
    invalid = client.create(title='', content='')
    assert invalid.status_code == 400
    assert invalid.json['error'] == {'code': 'validation_error', 'message': 'Enter a title or some text.'}
    too_long = client.create(title='x'*201)
    assert too_long.json['error']['message'] == 'Title must be text of at most 200 characters.'
    denied = client.client.post('/api/v1/records', json={'title': 'x'})
    assert denied.status_code == 403 and denied.json['error']['code'] == 'csrf_error'
    assert denied.json['error']['message'] == 'Page verification expired. Refresh and try again.'
    client.client.delete_cookie('everhere-language')
    response = client.client.get('/missing', headers={'X-Everhere-Language': 'en'})
    assert response.status_code == 404 and response.json['error']['message'] == 'The page or resource does not exist.'


def test_people_view_keeps_user_names_and_relations(client):
    person = client.call('POST', '/graph/entities', {'name': '人物'}).json['data']
    record = client.create(title='现在', linkedEntityIds=[person['id']]).json['data']
    client.client.set_cookie('everhere-language', 'en')
    people = client.call('GET', '/graph').json['data']['entities']
    assert people[0]['name'] == '人物'
    assert people[0]['recordCount'] == 1
    assert client.call('GET', '/records?node='+person['id']).json['data']['records'][0]['id'] == record['id']


def test_language_does_not_change_draft_or_failed_write(client):
    draft = client.call('POST', '/drafts', {'kind': 'record', 'values': {'title': '首页', 'content': '还没有写完', 'mood': '平静'}}).json['data']
    client.client.set_cookie('everhere-language', 'en')
    assert client.call('GET', '/drafts/'+draft['id']).json['data'] == draft
    result = client.call('PUT', '/drafts/'+draft['id'], {'version': draft['version']+5, 'values': {'title': 'overwrite'}})
    assert result.status_code == 409 and result.json['error']['code'] == 'draft_conflict'
    assert client.call('GET', '/drafts/'+draft['id']).json['data'] == draft


def test_shared_catalog_matches_generated_browser_module():
    root = Path(__file__).resolve().parents[1]
    catalog = json.loads((root/'app/locales/en.json').read_text(encoding='utf-8'))
    module = (root/'app/static/js/messages-en.js').read_text(encoding='utf-8').split('export default ', 1)[1].rstrip().removesuffix(';')
    assert json.loads(module) == catalog
