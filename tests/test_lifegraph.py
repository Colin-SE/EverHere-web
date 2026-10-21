"""人生脉络：有限邻域、正式来源、授权与同事实关系写入。"""
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.extensions import db
from app.models import LifeNode, LifeRecord, RecordNode
from conftest import Client


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr('app.services.lifegraph.graph_today', lambda: date(2026, 10, 21))


def data(response):
    assert response.status_code in (200, 201), response.json
    return response.json['data']


def person(client, name='小林'):
    return client.call('POST', '/graph/entities', {'name': name}).json['data']


def node(app, client, kind, name, **extra):
    with client.client.session_transaction() as session:
        owner = session['space_id']
    source = str(uuid4())
    subject = {'entities': 'entity', 'chapters': 'chapter', 'threads': 'thread'}[kind]
    native = {'type': subject, 'id': source, 'createdAt': '1', 'updatedAt': '1', 'deletedAt': None}
    if subject == 'entity':
        native.update(kind=extra.get('type', 'object'), name=name, meaning='属于同一份资料')
    else:
        native['title'] = name
    if subject == 'chapter':
        native.update(eventDate={'precision': 'range', 'start': '2026-09-01', 'end': '2027-06-30'}, threadIds=extra.get('threadIds', []))
    with app.app_context():
        db.session.add(LifeNode(user_id=owner, source_id=source, kind=kind, name=name, payload={'type': extra.get('type', 'custom'), 'summary': '属于同一份资料', 'androidDocument': native}))
        db.session.commit()
    return subject + ':' + source


def test_now_is_limited_time_context_not_recently_edited(client):
    for index in range(15):
        client.create(title=f'这段时间 {index}', eventDate='2026-10-20')
    old = client.create(title='刚补录的旧事', eventDate='1999-01-01').json['data']
    current = client.create(title='日期未知仍在进行', recordState='ongoing', completionState='started', eventDate='', datePrecision='unknown').json['data']
    first = data(client.call('GET', '/lifegraph/neighbors'))
    assert len(first['nodes']) <= 10 and first['nextCursor']
    assert 'record:' + current['id'] in {row['key'] for row in first['nodes']}
    assert old['id'] not in {row['id'] for row in first['nodes']}
    assert all(edge['type'] == 'time_context' and not edge['editable'] for edge in first['edges'])
    seen = set()
    page = first
    while True:
        ids = {row['id'] for row in page['nodes'] if row['type'] != 'now'}
        assert not seen.intersection(ids)
        seen.update(ids)
        if not page['nextCursor']:
            break
        page = data(client.call('GET', '/lifegraph/neighbors', query_string={'cursor': page['nextCursor']}))
    assert len(seen) == 16


def test_one_layer_preserves_shared_paths_and_no_inferred_person_edge(client):
    a, b = person(client, '小林'), person(client, '阿遥')
    record = client.create(eventDate='2026-10-20', linkedEntityIds=[a['id'], b['id']]).json['data']
    from_person = data(client.call('GET', '/lifegraph/neighbors', query_string={'focus': 'entity:' + a['id']}))
    assert {row['key'] for row in from_person['nodes']} == {'entity:' + a['id'], 'record:' + record['id']}
    from_record = data(client.call('GET', '/lifegraph/neighbors', query_string={'focus': 'record:' + record['id']}))
    assert len(from_record['edges']) == 2
    assert all(edge['source'] == 'record:' + record['id'] and edge['provenance'] == '用户保存的正式关联' for edge in from_record['edges'])
    assert all(edge['target'].startswith('entity:') for edge in from_record['edges'])
    client.create(eventDate='2026-10-20', linkedEntityIds=[a['id']])
    initial = data(client.call('GET', '/lifegraph/neighbors'))
    assert len([edge for edge in initial['edges'] if edge['type'] == 'record_entity' and edge['target'] == 'entity:' + a['id']]) == 2


def test_graph_does_not_apply_timeline_visibility_or_fabricate_dates(client):
    value = client.create(eventDate='2026-10', datePrecision='month', showInTimeline=False).json['data']
    page = data(client.call('GET', '/lifegraph/neighbors', query_string={'types': 'record', 'from': '2026-10-01', 'to': '2026-10-31'}))
    row = next(row for row in page['nodes'] if row['type'] == 'record')
    assert row['id'] == value['id'] and row['date'] == {'precision': 'month', 'start': '2026-10', 'end': None}
    empty = data(client.call('GET', '/lifegraph/neighbors', query_string={'types': 'person'}))
    assert [row['key'] for row in empty['nodes']] == ['now']


def test_spaces_and_deleted_or_protected_data_never_enter_graph(app, client):
    other = Client(app)
    p = person(client, '只能当前空间看到')
    r = client.create(title='私人正文', linkedEntityIds=[p['id']]).json['data']
    assert other.call('GET', '/lifegraph/neighbors', query_string={'focus': 'record:' + r['id']}).status_code == 404
    assert data(other.call('GET', '/lifegraph/search'))['nodes'] == []
    assert data(other.call('POST', '/lifegraph/snapshot', {'keys': ['entity:' + p['id'], 'record:' + r['id']]})) == {'nodes': [], 'edges': []}
    client.call('DELETE', '/records/' + r['id'], {'version': r['version']})
    page = data(client.call('GET', '/lifegraph/neighbors', query_string={'focus': 'entity:' + p['id']}))
    assert len(page['nodes']) == 1 and page['edges'] == []
    assert client.call('GET', '/lifegraph/neighbors', query_string={'focus': 'record:' + r['id']}).status_code == 404
    with app.app_context():
        row = db.session.scalar(select(LifeRecord).where(LifeRecord.source_id == r['id']))
        row.is_deleted = False
        row.privacy = 'vault'
        db.session.commit()
    assert client.call('GET', '/lifegraph/neighbors', query_string={'focus': 'record:' + r['id']}).status_code == 404


def test_cursor_bound_to_space_focus_filters_and_tampering(client, app):
    p = person(client)
    for _ in range(7):
        client.create(eventDate='2026-10-20', linkedEntityIds=[p['id']])
    page = data(client.call('GET', '/lifegraph/neighbors'))
    assert page['nextCursor']
    for args in [{'cursor': page['nextCursor'] + 'bad'}, {'cursor': page['nextCursor'], 'types': 'person'}, {'cursor': page['nextCursor'], 'focus': 'entity:' + p['id']}]:
        assert client.call('GET', '/lifegraph/neighbors', query_string=args).status_code == 409
    other = Client(app)
    assert other.call('GET', '/lifegraph/neighbors', query_string={'cursor': page['nextCursor']}).status_code == 409


def test_native_chapters_threads_objects_can_be_explored_without_new_facts(app, client):
    thread = node(app, client, 'threads', '学习摄影')
    chapter = node(app, client, 'chapters', '大学时期', threadIds=[thread.split(':', 1)[1]])
    camera = node(app, client, 'entities', '第一台相机', type='object')
    record = client.create(eventDate='2026-10-20', linkedEntityIds=[camera.split(':', 1)[1]], linkedChapterIds=[chapter.split(':', 1)[1]], linkedThreadIds=[thread.split(':', 1)[1]]).json['data']
    page = data(client.call('GET', '/lifegraph/neighbors', query_string={'focus': chapter}))
    assert {row['key'] for row in page['nodes']} == {chapter, thread, 'record:' + record['id']}
    assert any(edge['type'] == 'chapter_thread' and not edge['editable'] for edge in page['edges'])
    exported = data(client.call('GET', '/archive/export'))
    data(client.call('GET', '/lifegraph/neighbors', query_string={'focus': camera}))
    assert data(client.call('GET', '/archive/export'))['data'] == exported['data']


def test_explicit_link_unlink_updates_same_fact_and_native_archive_preserves_draft(client):
    p = person(client)
    r = client.create(title='原记录', eventDate='1960-02', datePrecision='month', content=' 原样正文\n').json['data']
    draft = data(client.call('POST', '/drafts', {'recordId': r['id']}))
    args = {'recordId': r['id'], 'nodeKey': 'entity:' + p['id'], 'version': r['version'], 'operation': 'link', 'confirmed': True}
    assert client.call('POST', '/lifegraph/relations', {**args, 'confirmed': False}).status_code == 400
    changed = data(client.call('POST', '/lifegraph/relations', args))
    assert changed['changed'] and changed['record']['id'] == r['id']
    saved = data(client.call('GET', '/records/' + r['id']))
    assert saved['content'] == r['content'] and saved['eventDate'] == '1960-02' and saved['linkedEntityIds'] == [p['id']]
    assert data(client.call('GET', '/drafts/' + draft['id']))['values'] == draft['values']
    assert client.call('POST', '/drafts/' + draft['id'] + '/commit', {'version': draft['version']}).status_code == 409
    assert client.call('POST', '/lifegraph/relations', args).status_code == 409
    args.update(version=saved['version'], operation='unlink')
    data(client.call('POST', '/lifegraph/relations', args))
    assert data(client.call('GET', '/records/' + r['id']))['linkedEntityIds'] == []
    assert len(data(client.call('GET', '/graph'))['entities']) == 1
    document = next(doc for doc in data(client.call('GET', '/archive/export'))['data']['documents'] if doc['id'] == r['id'])
    assert document['entityIds'] == [] and document['eventDate']['start'] == '1960-02'


def test_snapshot_recomputes_removed_paths_and_never_resurrects_deleted_records(client):
    p = person(client)
    r = client.create(eventDate='2026-10-20', linkedEntityIds=[p['id']]).json['data']
    keys = ['now', 'record:' + r['id'], 'entity:' + p['id']]
    assert len(data(client.call('POST', '/lifegraph/snapshot', {'keys': keys}))['edges']) == 2
    client.call('DELETE', '/records/' + r['id'], {'version': r['version']})
    snapshot = data(client.call('POST', '/lifegraph/snapshot', {'keys': keys}))
    assert {row['key'] for row in snapshot['nodes']} == {'now', 'entity:' + p['id']} and not snapshot['edges']


@pytest.mark.parametrize('args', [{'types': 'invalid'}, {'focus': 'garbage'}, {'from': 'not-a-date'}, {'from': '2026-10-22', 'to': '2026-10-21'}])
def test_invalid_queries_are_errors_not_empty_graphs(client, args):
    assert client.call('GET', '/lifegraph/neighbors', query_string=args).status_code == 400


def test_relation_cannot_cross_space_or_replace_record_record_with_invented_meaning(app, client):
    other = Client(app)
    p = person(other)
    r = client.create().json['data']
    args = {'recordId': r['id'], 'version': r['version'], 'nodeKey': 'entity:' + p['id'], 'confirmed': True, 'operation': 'link'}
    assert client.call('POST', '/lifegraph/relations', args).status_code == 404
    assert client.call('POST', '/lifegraph/relations', {**args, 'nodeKey': 'record:' + r['id']}).status_code == 400
    assert client.client.post('/api/v1/lifegraph/relations', json=args).status_code == 403


def test_native_record_relation_edit_preserves_original_fields_photos_and_audit(app, client):
    import json
    from io import BytesIO
    from pathlib import Path
    app.config['CLOUD_REGION'] = 'global'
    raw = (Path(__file__).parent / 'fixtures/android-native-v1.json').read_bytes()
    archive = json.loads(raw)
    preview = data(client.client.post('/api/v1/archive/files/preview', data={'archive': (BytesIO(raw), 'sample.json')}, headers={'X-CSRF-Token': client.token}))
    data(client.call('POST', '/archive/jobs/' + preview['id'] + '/confirm', {'confirmed': True, 'acceptMissingPhotos': True}))
    original = next(doc for doc in archive['data']['documents'] if doc['type'] == 'record' and doc['deletedAt'] is None)
    r = data(client.call('GET', '/records/' + original['id']))
    p = person(client, '新关联的人物')
    data(client.call('POST', '/lifegraph/relations', {'recordId': r['id'], 'version': r['version'], 'nodeKey': 'entity:' + p['id'], 'operation': 'link', 'confirmed': True}))
    exported = next(doc for doc in data(client.call('GET', '/archive/export'))['data']['documents'] if doc['id'] == r['id'])
    for field in original:
        if field not in ('updatedAt', 'entityIds'):
            assert exported[field] == original[field]
    assert set(exported['entityIds']) == {*original['entityIds'], p['id']}


def test_default_timezone_works_on_windows_and_bad_timezone_is_explicit_error(app, client, monkeypatch):
    monkeypatch.undo()
    assert client.call('GET', '/lifegraph/neighbors').status_code == 200
    app.config['EVENT_TIMEZONE'] = 'not/a/real/timezone'
    response = client.call('GET', '/lifegraph/neighbors')
    assert response.status_code == 503 and response.json['error']['code'] == 'graph_timezone_unavailable'


def test_search_keeps_exact_person_result_when_many_records_mention_same_name(client):
    p = person(client, '小林')
    for index in range(14):
        client.create(title=f'与小林的经历 {index}')
    result = data(client.call('GET', '/lifegraph/search', query_string={'q': '小林'}))
    assert len(result['nodes']) == 12 and result['hasMore']
    assert result['nodes'][0]['key'] == 'entity:' + p['id']
    assert client.call('GET', '/lifegraph/search', query_string={'q': 'x' * 101}).status_code == 400
    assert client.call('POST', '/lifegraph/snapshot', {'keys': ['now'] * 81}).status_code == 400
