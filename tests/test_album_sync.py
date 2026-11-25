"""Exercise the real Web routes and Android wire endpoints against one album."""
from hashlib import sha256
from io import BytesIO
from uuid import uuid4

import pytest
from PIL import Image

from conftest import Client
from test_shared_identity import PASSWORD, login_mobile, register_mobile, shared


class Phone:
    def __init__(self, app, email='shared@example.test'):
        tokens, self.installation = login_mobile(app, email=email)
        self.client = app.test_client()
        self.headers = {'Authorization': 'Bearer ' + tokens['accessToken'], 'X-Everhere-Region': 'cn',
                        'X-Everhere-Installation': self.installation}

    def sync(self, route, value):
        return self.client.post(f'/v1/sync/{route}', json=value, headers=self.headers)

    def envelope(self, doc, version='0'):
        return {'installationId': self.installation, 'operationId': str(uuid4()), 'localRevision': '1',
                'baseVersion': version, 'document': doc}

    def pull(self, cursor=None, limit=4):
        response = self.sync('pull', {'installationId': self.installation, 'cursor': cursor, 'limit': limit})
        assert response.status_code == 200, response.json
        return response.json

    def original(self, asset_id, raw=None):
        return self.client.open(f'/v1/assets/{asset_id}/original', method='GET' if raw is None else 'POST',
                                data=raw, content_type='application/octet-stream', headers=self.headers)


@pytest.fixture
def album(shared):
    app, _ = shared
    app.config['ALBUM_SYNC_ENABLED'] = True
    register_mobile(shared)
    web = Client(app)
    assert web.call('POST', '/accounts/login', {'email': 'shared@example.test', 'password': PASSWORD}).status_code == 200
    return app, web, Phone(app)


def png(color):
    buffer = BytesIO()
    Image.new('RGB', (4, 3), color).save(buffer, format='PNG')
    return buffer.getvalue()


def person(name):
    return {'type': 'entity', 'id': str(uuid4()), 'createdAt': '1700000000000', 'updatedAt': '1700000000000',
            'deletedAt': None, 'name': name, 'kind': 'person', 'meaning': '认识于大学'}


def record(person_id, specs=()):
    return {'type': 'record', 'id': str(uuid4()), 'createdAt': '1700000000000', 'updatedAt': '1700000000000',
            'deletedAt': None, 'title': '手机记录', 'content': '一段生活', 'recordState': 'occurred',
            'completionState': 'completed', 'eventDate': {'precision': 'month', 'start': '2026-11', 'end': None},
            'timezone': 'Asia/Shanghai', 'placeName': '北京', 'mood': None, 'coordinates': None,
            'administrativeArea': {'countryId': 'CHN', 'subdivisionId': '11'}, 'tags': ['校园'],
            'showInTimeline': True, 'showOnGlobe': False, 'privacy': 'standard', 'entityIds': [person_id],
            'threadIds': [], 'chapterIds': [], 'photos': list(specs)}


def test_both_directions_with_originals_and_new_install(album):
    app, web, phone = album
    first = phone.pull()
    assert first['items'] == []
    author = person('手机关联人物')
    assert phone.sync('push', phone.envelope(author)).json['document'] == author
    raw = png('brown')
    spec = {'id': str(uuid4()), 'sha256': sha256(raw).hexdigest(), 'mimeType': 'image/png',
            'byteSize': str(len(raw)), 'width': 4, 'height': 3}
    doc = record(author['id'], [spec])
    op = phone.envelope(doc)
    saved = phone.sync('push', op)
    assert saved.status_code == 200, saved.json
    assert saved.json['document'] == doc
    assert saved.json['serverVersion'] == '1'
    assert phone.sync('push', op).json == saved.json
    assert phone.sync('push', {**op, 'document': {**doc, 'title': '另一个请求'}}).json['error'] == 'operation_reused'

    url = '/records/' + doc['id']
    web_value = web.call('GET', url).json['data']
    assert web_value['linkedEntityIds'] == [author['id']]
    assert web_value['eventDate'] == '2026-11'
    photo_url = web_value['photoUris'][0]
    assert web.client.get(photo_url).status_code == 409
    assert phone.original(spec['id'], b'alt').json['error'] == 'original_integrity_failed'
    assert phone.original(spec['id'], raw).json['status'] == 'ready'
    assert phone.original(spec['id'], raw).json['status'] == 'ready'
    assert web.client.get(photo_url).data == raw
    assert web.client.get(photo_url + '/thumbnail').status_code == 200

    web_person = web.call('POST', '/graph/entities', {'name': '网页人物'}).json['data']
    web_raw = png('green')
    web_photo = web.call('POST', '/photos/batch', data={'requestKey': str(uuid4()), 'photos': (BytesIO(web_raw), 'new.png')}).json['data']['photos'][0]['uri']
    revised = web.call('PUT', url, {'version': 1, 'title': '在网页编辑', 'linkedEntityIds': [web_person['id']],
                                    'photoUris': [photo_url, web_photo]})
    assert revised.status_code == 200, revised.json
    assert revised.json['data']['version'] == 2
    second = phone.pull(first['cursor'])
    documents = [item['document'] for item in second['items']]
    record_latest = documents[-1]
    assert record_latest['title'] == '在网页编辑'
    assert record_latest['entityIds'] == [web_person['id']]
    assert record_latest['administrativeArea'] == doc['administrativeArea']
    assert phone.original(record_latest['photos'][1]['id']).data == web_raw

    clean_phone = Phone(app)
    pages = []
    current = None
    while True:
        result = clean_phone.pull(current, limit=2)
        pages.extend(result['items'])
        current = result['cursor']
        if not result['hasMore']:
            break
    assert [item['sequence'] for item in pages] == [item['sequence'] for item in second['items']]
    assert clean_phone.original(spec['id']).data == raw
    assert clean_phone.sync('pull', {'installationId': clean_phone.installation, 'limit': 4,
                                     'cursor': first['cursor']}).json['error'] == 'invalid_cursor'
    assert clean_phone.sync('pull', {'installationId': phone.installation, 'limit': 4,
                                     'cursor': None}).status_code == 403


def test_conflict_resolution_trash_and_account_isolation(album, shared):
    app, web, phone = album
    initial = web.create(title='最初').json['data']
    doc = phone.pull()['items'][0]['document']
    assert doc['id'] == initial['id']
    path = '/records/' + doc['id']
    assert web.call('PUT', path, {'version': 1, 'title': '网页稿'}).status_code == 200
    draft = {**doc, 'title': '离线手机稿'}
    op = phone.envelope(draft, '1')
    conflict = phone.sync('push', op).json
    assert conflict['status'] == 'conflict'
    assert phone.sync('push', op).json == conflict
    assert conflict['remote']['document']['title'] == '网页稿'
    listing = {'installationId': phone.installation, 'afterId': None, 'limit': 4}
    assert phone.sync('conflicts', listing).json['conflicts'][0]['local']['title'] == '离线手机稿'

    register_mobile(shared, 'other@example.test')
    other = Phone(app, 'other@example.test')
    assert other.pull()['items'] == []
    assert other.original('some-asset').status_code == 404
    resolve = {'conflictId': conflict['conflictId'], 'choice': 'both', 'expectedRemoteVersion': '2',
               'operation': phone.envelope({**draft, 'id': str(uuid4())})}
    other_op = {**resolve['operation'], 'installationId': other.installation}
    assert other.sync('resolve', {**resolve, 'operation': other_op}).status_code == 404
    result = phone.sync('resolve', resolve)
    assert result.status_code == 200, result.json
    assert result.json['status'] == 'resolved'
    assert phone.sync('resolve', resolve).json == result.json
    assert phone.sync('conflicts', listing).json['conflicts'] == []
    assert web.call('GET', path).json['data']['title'] == '网页稿'

    cursor = phone.pull()['cursor']
    assert web.call('DELETE', path, {'version': 2}).status_code == 200
    tombstone = phone.pull(cursor)
    doc = tombstone['items'][0]['document']
    assert doc['deletedAt'] is not None
    assert web.call('GET', path).status_code == 404
    restore = phone.sync('push', phone.envelope({**doc, 'deletedAt': None}, '3'))
    assert restore.status_code == 200, restore.json
    assert restore.json['serverVersion'] == '4'
    assert web.call('GET', path).json['data']['title'] == '网页稿'
