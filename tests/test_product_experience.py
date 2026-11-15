"""P1–P3 回归使用隔离资料和确定性的任务执行。"""
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from threading import Barrier
from uuid import uuid4

import pytest

from app.extensions import db
from app.models import Photo, now
from app.models_workflow import MemoirJob, ShopOrder, OrderEvent
from app.services import memoir_jobs
from conftest import Client
from test_workflows import administrator, action, draft, image_bytes, order_body, product, register, submit, upload


def test_album_page_and_draft_receipt_are_owner_scoped(app, client):
    draft = client.call('POST', '/drafts', {'kind': 'record', 'values': {'title': '受保护的输入'}}).json['data']
    path = '/drafts/' + draft['id']
    assert client.call('GET', path + '/receipt').json['data']['committed'] is False
    committed = client.call('POST', path + '/commit', {'version': draft['version']}).json['data']
    assert client.call('GET', path + '/receipt').json['data']['id'] == committed['id']
    assert Client(app).call('GET', path + '/receipt').status_code == 404
    for index in range(33):
        client.create(title=f'记录 {index}', eventDate=f'2026-10-{(index % 28) + 1:02d}')
    first = client.call('GET', '/records?page=1').json['data']
    second = client.call('GET', '/records?page=2').json['data']
    assert first['total'] == 34 and len(first['records']) == 30 and len(second['records']) == 4
    assert not {r['id'] for r in first['records']} & {r['id'] for r in second['records']}
    session = client.call('GET', '/auth/session').json['data']
    response = client.client.post('/api/v1/records', json={'title': '不应提交'}, headers={
        'X-CSRF-Token': client.token, 'X-Everhere-Space': str(uuid4()),
    })
    assert session['spaceId'] and response.status_code == 409 and response.json['error']['code'] == 'space_changed'


def test_photo_upload_reconciles_an_uncertain_batch_without_duplicates(app, client):
    key = str(uuid4())
    def photo_request(actor, count=2):
        return actor.client.post('/api/v1/photos/batch', data={
            'requestKey': key, 'photos': [(BytesIO(image_bytes()), f'{i}.png') for i in range(count)],
        }, headers={'X-CSRF-Token': actor.token})

    first = photo_request(client)
    assert first.status_code == 201
    assert photo_request(client).json == first.json
    assert photo_request(client, 1).status_code == 409
    other = Client(app)
    second = photo_request(other).json
    assert second != first
    for row in first.json['data']['photos']:
        assert other.client.get(row['uri']).status_code == 404
        assert other.client.get(row['uri'] + '/thumbnail').status_code == 404
        assert client.client.get(row['uri'] + '/thumbnail').mimetype == 'image/jpeg'
    with app.app_context():
        assert db.session.query(Photo).count() == 4


def test_connection_neighborhood_only_exposes_current_associations(app, client):
    person = client.call('POST', '/graph/entities', {'name': '朋友'}).json['data']
    ids = []
    for _ in range(18):
        ids.append(client.create(linkedEntityIds=[person['id']]).json['data']['id'])
    query = '/connections?kind=person&id=' + person['id']
    page = client.call('GET', query).json['data']
    assert page['source'] == 'record_association' and len(page['nodes']) == 16 and page['hasMore']
    assert len(client.call('GET', query + '&page=2').json['data']['nodes']) == 2
    foreign = Client(app)
    assert foreign.call('GET', query).status_code == 404
    record = client.call('GET', '/records/' + ids[0]).json['data']
    assert client.call('DELETE', '/records/' + ids[0], {'version': record['version']}).status_code == 200
    assert client.call('GET', '/connections?kind=record&id=' + ids[0]).status_code == 404
    assert client.client.get('/places').status_code == 200


def test_order_staff_buyer_roundtrip_preserves_price_and_internal_privacy(app, client):
    buyer = register(client)
    admin, second = administrator(app), administrator(app, 'second@example.test')
    item = product(admin, photoRequired=True)
    data = order_body(item, photoUri=upload(client), authorisePhoto=True)
    order = client.call('POST', '/shop/orders', data).json['data']
    path = '/admin/orders/' + order['id']
    user_path = '/shop/orders/' + order['id']
    assert client.call('GET', '/shop/orders/by-request/' + data['requestKey']).json['data']['id'] == order['id']
    assert client.call('POST', '/shop/orders', data).json['data']['replayed']
    assert client.call('GET', path).status_code == 403
    before = admin.call('GET', path).json['data']
    assert before['items'][0]['snapshot'].get('customText') is None
    assert admin.call('GET', '/admin/orders?buyer=' + buyer['id'] + '&kind=medal').json['data']['total'] == 1
    def change(actor, previous, operation, message=''):
        return actor.call('POST', path + '/process', {'version': previous['version'], 'action': operation, 'message': message})
    claimed = change(admin, before, 'claim').json['data']
    assert change(admin, before, 'claim').json['data']['version'] == claimed['version']
    assert change(second, before, 'claim').status_code == 409
    assert admin.client.get(claimed['items'][0]['photoUrl']).data == image_bytes()
    assert second.client.get(claimed['items'][0]['photoUrl']).status_code == 404
    note = change(admin, claimed, 'note', '仅内部可见').json['data']
    asked = change(admin, note, 'request_info', '请确认刻字').json['data']
    visible = client.call('GET', user_path).json['data']
    assert visible['processingState'] == 'needs_info' and [e['message'] for e in visible['events']] == ['', '请确认刻字']
    reply = client.call('POST', user_path + '/reply', {'version': asked['version'], 'message': '刻字已确认'}).json['data']
    complete = change(admin, reply, 'complete').json['data']
    assert complete['processingState'] == 'completed' and complete['totalCents'] == order['totalCents']
    assert complete['state'] == 'unpaid' and complete['paymentAvailable'] is False
    assert Client(app).call('GET', user_path).status_code == 401
    assert admin.call('GET', '/admin/orders?status=resolved').json['data']['total'] == 1
    with app.app_context():
        assert db.session.get(ShopOrder, order['id']).state == 'unpaid'
        assert db.session.query(OrderEvent).count() == 5


def test_gallery_and_product_detail_hide_unlisted_media(app, client):
    admin = administrator(app)
    item = product(admin)
    path = '/api/v1/admin/products/' + item['id']
    result = admin.client.post(path + '/gallery', data={'version': str(item['version']), 'image': (BytesIO(image_bytes()), 'gallery.png')},
                               headers={'X-CSRF-Token': admin.token})
    assert result.status_code == 201
    item = result.json['data']
    assert client.client.get(item['gallery'][0]['url']).status_code == 200
    assert client.call('GET', '/shop/products?kind=gift').json['data']['products'] == []
    assert client.call('GET', '/shop/products?kind=medal&q=旅行').json['data']['products'][0]['id'] == item['id']
    update = admin.call('PUT', path.removeprefix('/api/v1'), {**item, 'active': False})
    assert update.status_code == 200
    assert client.call('GET', '/shop/products/' + item['id']).status_code == 404
    assert client.client.get(item['gallery'][0]['url']).status_code == 404


def test_background_job_reclaims_interrupted_attempt_once(app, client):
    register(client)
    memoir, _ = draft(client)
    admin = administrator(app)
    approved = action(admin, action(admin, submit(client, memoir), 'claim').json['data'], 'review', decision='approve').json['data']
    accepted = action(admin, approved, 'generate', background=True)
    assert accepted.status_code == 202 and accepted.json['data']['generation']['state'] == 'queued'
    assert action(admin, approved, 'generate', background=True).status_code == 202
    with app.app_context():
        job = db.session.get(MemoirJob, approved['revisionId'])
        job.state, job.attempt, job.updated_at = 'running', 1, now() - timedelta(minutes=12)
        db.session.commit()
        assert memoir_jobs.run_job(approved['revisionId'])
        assert not memoir_jobs.run_job(approved['revisionId'])
    ready = client.call('GET', '/memoirs/' + memoir['id']).json['data']
    assert ready['state'] == 'ready' and ready['generation']['state'] == 'succeeded'
    assert client.client.get(ready['previewUrl']).status_code == 200


def test_two_order_workers_can_only_claim_once(app, client):
    with app.app_context():
        if db.engine.dialect.name != 'mysql':
            pytest.skip('Requires MySQL locking')
    register(client)
    first, second = administrator(app), administrator(app, 'parallel@example.test')
    order = client.call('POST', '/shop/orders', order_body(product(first))).json['data']
    barrier = Barrier(2, timeout=10)

    def claim(staff):
        barrier.wait()
        return staff.call('POST', '/admin/orders/' + order['id'] + '/process',
                          {'action': 'claim', 'version': order['version']}).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(claim, (first, second))) == [200, 409]
    with app.app_context():
        assert db.session.query(OrderEvent).filter_by(order_id=order['id'], action='claim').count() == 1
