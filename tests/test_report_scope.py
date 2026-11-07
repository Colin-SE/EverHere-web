"""按用户确认的 F1—F4 范围验证移除入口、样张和同源地点回看。"""
from io import BytesIO

import pytest
from pypdf import PdfReader
from sqlalchemy import select

from app.extensions import db
from app.models import LifeNode, LifeRecord, Photo
from app.models_workflow import MemoirAsset
from app.services import memoir_pdf
from conftest import Client
from test_workflows import administrator, register, draft, submit, action, product, order_body, upload, image_bytes


@pytest.mark.parametrize('method,path', [
    ('GET', '/lifegraph'), ('GET', '/lifegraph/neighbors'),
    ('GET', '/lifegraph/search?q=test'), ('POST', '/lifegraph/relations'),
    ('GET', '/archive/export'), ('GET', '/archive/export.zip'),
    ('POST', '/archive/preview'), ('POST', '/archive/import'),
    ('POST', '/archive/files/preview'), ('GET', '/archive/jobs'),
    ('GET', '/cloud/status'), ('POST', '/cloud/login'),
    ('POST', '/cloud/logout'), ('POST', '/cloud/push'), ('POST', '/cloud/pull'),
    ('POST', '/shop/orders/any/pay'), ('POST', '/shop/orders/any/cancel'),
    ('POST', '/shop/orders/any/refund'), ('POST', '/admin/orders/any/ship'),
])
def test_removed_features_have_no_callable_routes(client, method, path):
    assert client.call(method, path, {} if method == 'POST' else None).status_code == 404


def test_ui_and_old_static_urls_expose_only_current_scope(client):
    page = client.client.get('/').text
    for view in ['lifegraph', 'archive', 'appearance']:
        assert f'data-view="{view}"' not in page
    for path in ['js/lifegraph.js', 'js/lifegraph-state.js', 'css/lifegraph.css', 'js/login.js']:
        assert client.client.get('/static/'+path).status_code == 404
    assert client.client.get('/login').location.endswith('/workspace#account')
    assert 'cloudConfigured' not in client.call('GET', '/auth/session').json['data']


def test_places_include_names_without_coordinates_and_keep_owner_isolation(app, client):
    record = client.create(placeName='大学图书馆', latitude=None, longitude=None).json['data']
    client.create(title='没有地点')
    places = client.call('GET', '/records?target=spatial').json['data']['records']
    assert [r['id'] for r in places] == [record['id']]
    assert Client(app).call('GET', '/records?target=spatial').json['data']['records'] == []
    changed = client.call('PUT', '/records/'+record['id'], {**record, 'placeName': '新图书馆'}).json['data']
    assert client.call('GET', '/records?target=spatial').json['data']['records'][0] == changed


def test_overdue_plan_does_not_become_an_occurred_record(client):
    plan = client.create(recordState='planned', eventDate='2000-01-01').json['data']
    for target in ['all', 'timeline']:
        assert client.call('GET', '/records?target='+target).json['data']['records'][0]['recordState'] == 'planned'
    assert client.call('GET', '/records/'+plan['id']).json['data']['version'] == plan['version']


def test_existing_imported_metadata_survives_edit_delete_and_restore(app, client):
    record = client.create(datePrecision='month', eventDate='1960-02', timezone='GMT', tags=['旧标签', '旧标签']).json['data']
    native = {'type': 'record', 'id': record['id'], 'createdAt': '1000', 'updatedAt': '1000', 'deletedAt': None,
              'title': record['title'], 'content': record['content'], 'recordState': 'occurred', 'completionState': 'completed',
              'eventDate': {'precision': 'month', 'start': '1960-02', 'end': None}, 'timezone': 'GMT',
              'placeName': None, 'coordinates': None, 'tags': ['旧标签', '旧标签'], 'mood': None,
              'showInTimeline': True, 'showOnGlobe': False, 'privacy': 'standard',
              'entityIds': [], 'threadIds': [], 'chapterIds': [], 'photos': []}
    # 仅在合成库直接建立已有元数据，不恢复已删除的归档导入功能。
    with app.app_context():
        row = db.session.scalar(select(LifeRecord).where(LifeRecord.source_id == record['id']))
        row.payload = {**row.payload, 'androidDocument': native}
        db.session.commit()
    edited = client.call('PUT', '/records/'+record['id'], {**record, 'title': '编辑后标题'}).json['data']
    assert edited['androidDocument']['title'] == '编辑后标题'
    for key in ['id', 'createdAt', 'eventDate', 'timezone', 'tags']:
        assert edited['androidDocument'][key] == native[key]
    deleted = client.call('DELETE', '/records/'+record['id'], {'version': edited['version']})
    assert deleted.status_code == 200
    restored = client.call('POST', '/records/'+record['id']+'/restore', {'version': deleted.json['data']['version']}).json['data']
    assert restored['id'] == record['id'] and restored['androidDocument']['deletedAt'] is None
    assert restored['androidDocument']['createdAt'] == '1000'


def test_only_people_are_exposed_from_legacy_node_storage(app, client):
    client.call('POST', '/graph/entities', {'name': '我的朋友'})
    with client.client.session_transaction() as session:
        space_id = session['space_id']
    with app.app_context():
        node = LifeNode(user_id=space_id, source_id='legacy-pet', kind='entities', name='宠物', payload={'type': 'pet'})
        db.session.add(node)
        db.session.commit()
    assert [n['name'] for n in client.call('GET', '/graph').json['data']['entities']] == ['我的朋友']
    assert client.call('PUT', '/graph/entities/legacy-pet', {'name': '新名称', 'version': 1}).status_code == 404
    assert client.call('DELETE', '/graph/entities/legacy-pet', {'version': 1}).status_code == 404


def snapshot(chapters):
    return {'title': 'A memory book', 'theme': 'Our travels', 'chapters': [
        {'heading': f'Chapter {i}', 'date': None, 'content': f'PRIVATE_CHAPTER_{i}', 'photoAssetIds': []}
        for i in range(chapters)]}


@pytest.mark.parametrize('chapters', [1, 2, 4])
def test_preview_is_strictly_a_subset_and_has_no_hidden_remaining_pages(chapters):
    final = memoir_pdf.render_pdf(snapshot(chapters), {}, {})
    preview = memoir_pdf.sample_pdf(final)
    full_reader, sample_reader = PdfReader(BytesIO(final)), PdfReader(BytesIO(preview))
    assert 0 < len(sample_reader.pages) <= 2
    assert len(sample_reader.pages) < len(full_reader.pages)
    text = '\n'.join(page.extract_text() for page in sample_reader.pages)
    assert 'SAMPLE PAGES ONLY' in text
    assert f'PRIVATE_CHAPTER_{chapters - 1}' not in text
    # 再检查所有对象流，确保被省略的页并非只在页面树里隐藏。
    for objects in sample_reader.xref.values():
        for object_id in objects:
            from pypdf.generic import IndirectObject
            obj = sample_reader.get_object(IndirectObject(object_id, 0, sample_reader))
            if hasattr(obj, 'get_data'):
                assert f'PRIVATE_CHAPTER_{chapters - 1}'.encode() not in obj.get_data()


def ready_memoir(app, client):
    register(client)
    memoir, _ = draft(client)
    admin = administrator(app)
    queued = submit(client, memoir)
    claimed = action(admin, queued, 'claim').json['data']
    approved = action(admin, claimed, 'review', decision='approve').json['data']
    ready = action(admin, approved, 'generate').json['data']
    return ready, admin


def test_old_full_length_preview_is_never_served_and_final_url_is_unavailable(app, client):
    ready, _ = ready_memoir(app, client)
    with app.app_context():
        assets = {a.kind: a for a in db.session.scalars(select(MemoirAsset).where(MemoirAsset.revision_id == ready['revisionId']))}
        final, final_id = assets['final'].data, assets['final'].id
        assets['preview'].data = final  # 模拟旧版完整预览，升级不需要修改真实资料。
        db.session.commit()
    response = client.client.get(ready['previewUrl'])
    assert response.status_code == 200
    assert len(PdfReader(BytesIO(response.data)).pages) < len(PdfReader(BytesIO(final)).pages)
    for path in [f"/memoirs/{ready['id']}/assets/{final_id}", f"/memoirs/{ready['id']}/final.pdf"]:
        assert client.call('GET', path).status_code == 404


def test_sample_failure_does_not_mark_production_ready(app, client, monkeypatch):
    register(client)
    memoir, _ = draft(client)
    admin = administrator(app)
    approved = action(admin, action(admin, submit(client, memoir), 'claim').json['data'], 'review', decision='approve').json['data']
    def fail(_):
        raise ValueError('synthetic sample failure')
    monkeypatch.setattr(memoir_pdf, 'sample_pdf', fail)
    failed = action(admin, approved, 'generate')
    assert failed.status_code == 422 and failed.json['data']['state'] == 'approved'
    with app.app_context():
        assert db.session.scalar(select(MemoirAsset).where(MemoirAsset.kind.in_(['final', 'preview']))) is None


def test_second_claim_is_rejected_and_original_reviewer_is_retained(app, client):
    register(client)
    memoir, _ = draft(client)
    first, second = administrator(app), administrator(app, 'second@example.test')
    queued = submit(client, memoir)
    claimed = action(first, queued, 'claim').json['data']
    assert action(second, queued, 'claim').status_code == 409
    assert second.call('GET', '/admin/memoirs/'+memoir['id']).status_code == 403
    assert first.call('GET', '/admin/memoirs/'+memoir['id']).json['data']['reviewerId'] == claimed['reviewerId']


def test_order_keeps_photo_bytes_when_source_changes_and_blocks_other_users(app, client):
    register(client)
    admin = administrator(app)
    catalogue, photo_uri = product(admin, photoRequired=True), upload(client)
    request = order_body(catalogue, photoUri=photo_uri, authorisePhoto=True)
    order = client.call('POST', '/shop/orders', request).json['data']
    with app.app_context():
        photo = db.session.get(Photo, photo_uri.rsplit('/', 1)[-1])
        photo.data = b'changed source'
        db.session.commit()
        from app.models_workflow import ShopOrderItem
        item = db.session.scalar(select(ShopOrderItem).where(ShopOrderItem.order_id == order['id']))
        assert item.photo_data == image_bytes()
    stranger = Client(app)
    register(stranger, 'another@example.test')
    assert stranger.call('GET', '/shop/orders/'+order['id']).status_code == 404
    assert client.call('GET', '/shop/orders/'+order['id']).json['data']['paymentAvailable'] is False
