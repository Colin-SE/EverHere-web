"""用合成资料验证跨角色完整工作流、隐私边界、冲突与失败回滚。"""
from io import BytesIO
from uuid import uuid4

import pytest
from PIL import Image
from sqlalchemy import select

from conftest import Client
from app.extensions import db
from app.models import LifeRecord, Photo
from app.models_workflow import Member, MemoirAsset, MemoirRevision, ShopOrder, ShopOrderItem


def register(client, email='owner@example.test', claim=True):
    result = client.call('POST', '/accounts/register', {'email': email, 'password': 'test-password-123', 'name': '测试用户', 'claimCurrentSpace': claim, 'role': 'admin'})
    assert result.status_code == 201, result.json
    return result.json['data']['member']


def administrator(app, email='admin@example.test'):
    runner = app.test_cli_runner()
    result = runner.invoke(args=['create-admin', '--email', email, '--name', '制作管理员', '--password', 'admin-password-123'])
    assert result.exit_code == 0, result.output
    client = Client(app)
    result = client.call('POST', '/accounts/login', {'email': email, 'password': 'admin-password-123'})
    assert result.status_code == 200, result.json
    return client


def image_bytes():
    output = BytesIO()
    Image.new('RGB', (30, 20), 'green').save(output, format='PNG')
    return output.getvalue()


def upload(client):
    result = client.client.post('/api/v1/photos', data={'photo': (BytesIO(image_bytes()), 'selected.png')}, headers={'X-CSRF-Token': client.token})
    assert result.status_code == 201
    return result.json['data']['uri']


def draft(client, record=None, photo=False):
    record = record or client.create(title='七天旅行', content='旅途中有意义的经历。', photoUris=[upload(client)] if photo else []).json['data']
    result = client.call('POST', '/memoirs', {'title': '旅行回忆录', 'theme': '一个完整的故事', 'chapters': [
        {'recordId': record['id'], 'version': record['version'], 'heading': '第一天', 'photoUris': record['photoUris'] if photo else []}]})
    assert result.status_code == 201, result.json
    return result.json['data'], record


def submit(client, memoir):
    result = client.call('POST', f"/memoirs/{memoir['id']}/submit", {'version': memoir['version'], 'authoriseMaterials': True})
    assert result.status_code == 201, result.json
    return result.json['data']


def action(client, memoir, action_name, **changes):
    return client.call('POST', f"/admin/memoirs/{memoir['id']}/{action_name}", {'version': memoir['version'], 'revisionId': memoir['revisionId'], **changes})


def product(admin, kind='medal', **changes):
    result = admin.call('POST', '/admin/products', {'name': '旅行纪念奖牌', 'description': '独立购买，无需回忆录', 'active': True, 'variants': [
        {'name': '标准款', 'kind': kind, 'priceCents': 3900, 'textRequired': kind == 'medal', **changes}]})
    assert result.status_code == 201, result.json
    return result.json['data']


def order_body(product, **changes):
    variant = product['variants'][0]
    return {'requestKey': str(uuid4()), 'items': [{'variantId': variant['id'], 'variantVersion': variant['version'], 'productVersion': product['version'], 'quantity': 2, 'customText': '我的日本旅行', **changes}]}


def test_explicit_account_claim_keeps_ids_and_revokes_old_guest_cookie(app, client):
    static = client.client.get('/static/images/mobile/app_icon.svg')
    assert 'Set-Cookie' not in static.headers
    record = client.create().json['data']
    cookie = client.client.get_cookie('session')
    former_guest = Client(app)
    former_guest.client.set_cookie('session', cookie.value)
    member = register(client)
    assert member['role'] == 'user'
    assert client.call('GET', '/records/'+record['id']).status_code == 200
    assert former_guest.call('GET', '/records/'+record['id']).status_code == 404
    assert client.client.post('/api/v1/memoirs', json={}).status_code == 403
    assert client.call('POST', '/accounts/logout', {}).status_code == 200
    assert client.call('GET', '/records/'+record['id']).status_code == 404
    result = client.call('POST', '/accounts/login', {'email': 'OWNER@example.test', 'password': 'test-password-123'})
    assert result.status_code == 200
    assert client.call('GET', '/records/'+record['id']).json['data']['id'] == record['id']


def test_registration_without_claim_does_not_silently_move_guest_records(app, client):
    record = client.create().json['data']
    cookie = client.client.get_cookie('session')
    register(client, claim=False)
    assert client.call('GET', '/records/'+record['id']).status_code == 404
    guest = Client(app)
    guest.client.set_cookie('session', cookie.value)
    assert guest.call('GET', '/records/'+record['id']).status_code == 200
    assert client.call('POST', '/accounts/logout', {}).status_code == 200
    assert client.call('GET', '/records/'+record['id']).status_code == 200
    assert client.call('POST', '/accounts/login', {'email': 'owner@example.test', 'password': 'test-password-123'}).status_code == 200
    assert client.call('GET', '/records/'+record['id']).status_code == 404


def test_workflow_english_ui_errors_keep_user_content_and_codes(app, client):
    client.client.set_cookie('everhere-language', 'en')
    page = client.client.get('/workspace')
    assert '<html lang="en">' in page.text and 'Creative Shop' in page.text
    assert client.call('GET', '/memoirs').json['error'] == {'code': 'login_required', 'message': 'Sign in to your account first.'}
    register(client)
    record = client.create(title='商品名称', content='用户原文不翻译').json['data']
    memoir, _ = draft(client, record)
    assert memoir['title'] == '旅行回忆录'
    submitted = submit(client, memoir)
    assert submitted['revision']['snapshot']['chapters'][0]['content'] == '用户原文不翻译'
    denied = client.call('GET', '/admin/products')
    assert denied.status_code == 403 and denied.json['error']['message'] == 'This action requires administrator access.'


def test_two_roles_return_resubmit_generate_and_keep_immutable_selected_material(app, client):
    register(client)
    memoir, record = draft(client, photo=True)
    admin = administrator(app)
    other_admin = administrator(app, 'otheradmin@example.test')
    stranger = Client(app)
    register(stranger, 'stranger@example.test')
    assert stranger.call('GET', '/memoirs/'+memoir['id']).status_code == 404
    assert stranger.call('GET', '/admin/memoirs').status_code == 403
    assert client.call('POST', f"/memoirs/{memoir['id']}/submit", {'version': memoir['version']}).status_code == 400
    submitted = submit(client, memoir)
    original = submitted['revision']['snapshot']
    selected_id = original['chapters'][0]['photoAssetIds'][0]
    asset_url = f"/api/v1/memoirs/{memoir['id']}/assets/{selected_id}"
    assert admin.client.get(asset_url).status_code == 403
    assert stranger.client.get(asset_url).status_code == 404
    queue = admin.call('GET', '/admin/memoirs').json['data']['memoirs'][0]
    assert 'title' not in queue and 'revision' not in queue
    claimed = action(admin, submitted, 'claim').json['data']
    assert other_admin.client.get(asset_url).status_code == 403
    assert admin.client.get(asset_url).data == image_bytes()
    assert admin.client.get(record['photoUris'][0]).status_code == 404
    assert admin.call('PUT', '/records/'+record['id'], {**record, 'title': '非法修改'}).status_code == 404
    assert client.call('PUT', '/memoirs/'+memoir['id'], {**memoir, 'version': claimed['version']}).status_code == 409
    assert action(admin, claimed, 'review', decision='return').status_code == 400
    returned = action(admin, claimed, 'review', decision='return', reason='请补充旅行结尾').json['data']
    edited_record = client.call('PUT', '/records/'+record['id'], {**record, 'content': '新的旅行结尾。'}).json['data']
    assert client.call('GET', '/memoirs/'+memoir['id']).json['data']['revision']['snapshot'] == original
    assert client.call('POST', f"/memoirs/{memoir['id']}/submit", {'version': returned['version'], 'authoriseMaterials': True}).status_code == 409
    updated = client.call('PUT', '/memoirs/'+memoir['id'], {**returned, 'title': '尚未授权的新草稿标题', 'theme': '尚未授权的新主题', 'chapters': [{'recordId': record['id'], 'version': edited_record['version'], 'heading': '完整旅程', 'photoUris': record['photoUris']}]}).json['data']
    staff_view = admin.call('GET', '/admin/memoirs/'+memoir['id']).json['data']
    staff_queue = admin.call('GET', '/admin/memoirs').json['data']['memoirs'][0]
    assert staff_view['title'] == staff_queue['title'] == original['title']
    assert staff_view['theme'] == staff_queue['theme'] == original['theme']
    resubmitted = submit(client, updated)
    assert resubmitted['revisionNumber'] == 2
    assert action(admin, returned, 'review', decision='approve').status_code == 409
    claimed = action(admin, resubmitted, 'claim').json['data']
    approved = action(admin, claimed, 'review', decision='approve').json['data']
    assert action(other_admin, approved, 'generate').status_code == 403
    ready_result = action(admin, approved, 'generate')
    assert ready_result.status_code == 200, ready_result.json
    ready = ready_result.json['data']
    assert ready['state'] == 'ready'
    preview = client.client.get(ready['previewUrl'])
    assert preview.status_code == 200 and preview.data.startswith(b'%PDF')
    assert 'no-store' in preview.headers['Cache-Control']
    assert stranger.client.get(ready['previewUrl']).status_code == 404
    assert client.client.get(f"/api/v1/memoirs/{memoir['id']}/assets/{selected_id}").status_code == 404
    with app.app_context():
        rows = list(db.session.scalars(select(MemoirRevision).where(MemoirRevision.memoir_id == memoir['id']).order_by(MemoirRevision.number)))
        assert rows[0].snapshot == original and rows[0].reason == '请补充旅行结尾'
        assert rows[1].snapshot['chapters'][0]['content'] == '新的旅行结尾。'
        final = db.session.scalar(select(MemoirAsset).where(MemoirAsset.revision_id == rows[1].id, MemoirAsset.kind == 'final'))
        assert client.client.get(f"/api/v1/memoirs/{memoir['id']}/assets/{final.id}").status_code == 404


def test_failed_generation_keeps_approved_snapshot_then_retries(app, client, monkeypatch):
    from app.services import memoir_pdf
    register(client)
    memoir, _ = draft(client)
    admin = administrator(app)
    submitted = submit(client, memoir)
    claimed = action(admin, submitted, 'claim').json['data']
    approved = action(admin, claimed, 'review', decision='approve').json['data']
    original_renderer = memoir_pdf.render_pdf
    def fail(*args, **kwargs):
        raise OSError('synthetic renderer failure')
    monkeypatch.setattr(memoir_pdf, 'render_pdf', fail)
    failed = action(admin, approved, 'generate')
    assert failed.status_code == 422
    retained = failed.json['data']
    assert retained['state'] == 'approved' and retained['renderError']
    assert retained['revision']['snapshot'] == approved['revision']['snapshot']
    assert client.client.get(f"/api/v1/memoirs/{memoir['id']}/preview.pdf").status_code == 409
    with app.app_context():
        assert db.session.scalar(select(MemoirAsset).where(MemoirAsset.kind == 'final')) is None
    monkeypatch.setattr(memoir_pdf, 'render_pdf', original_renderer)
    assert action(admin, retained, 'generate').json['data']['state'] == 'ready'


@pytest.mark.parametrize('change', [{'chapters': []}, {'chapters': 'bad'}, {'title': ''}])
def test_invalid_submission_does_not_create_revision(app, client, change):
    register(client)
    memoir, _ = draft(client)
    if change.get('chapters') == []:
        updated = client.call('PUT', '/memoirs/'+memoir['id'], {**memoir, **change}).json['data']
        assert client.call('POST', '/memoirs/'+memoir['id']+'/submit', {'version': updated['version'], 'authoriseMaterials': True}).status_code == 400
    else:
        assert client.call('PUT', '/memoirs/'+memoir['id'], {**memoir, **change}).status_code == 400
    with app.app_context():
        assert db.session.scalar(select(MemoirRevision)) is None


def test_ordinary_gift_order_is_independent_private_idempotent_and_price_snapshot(app, client):
    register(client)
    admin = administrator(app)
    catalogue = product(admin)
    assert client.call('POST', '/admin/products', {}).status_code == 403
    request = order_body(catalogue)
    result = client.call('POST', '/shop/orders', request)
    assert result.status_code == 201, result.json
    order = result.json['data']
    assert order['state'] == 'unpaid' and order['totalCents'] == 7800 and not order['paymentAvailable']
    repeated = client.call('POST', '/shop/orders', request)
    assert repeated.json['data']['id'] == order['id'] and repeated.json['data']['replayed']
    changed = {**request, 'items': [{**request['items'][0], 'quantity': 1}]}
    assert client.call('POST', '/shop/orders', changed).status_code == 409
    stranger = Client(app)
    register(stranger, 'stranger@example.test')
    assert stranger.call('GET', '/shop/orders/'+order['id']).status_code == 404
    catalogue['variants'][0]['priceCents'] = 9900
    revised = admin.call('PUT', '/admin/products/'+catalogue['id'], catalogue)
    assert revised.status_code == 200
    assert client.call('GET', '/shop/orders/'+order['id']).json['data']['totalCents'] == 7800
    assert client.call('POST', '/shop/orders', order_body(catalogue)).json['error']['code'] == 'price_changed'
    assert client.call('POST', '/shop/orders/'+order['id']+'/pay', {}).status_code == 404


@pytest.mark.parametrize('change,code', [({'customText': ''}, 'customText'), ({'quantity': 0}, 'quantity'), ({'quantity': True}, 'quantity'), ({'revisionId': 'missing'}, 'revisionId'), ({'photoUri': '/api/v1/photos/missing'}, 'photoUri')])
def test_order_validation_rolls_back_without_partial_order(app, client, change, code):
    register(client)
    catalogue = product(administrator(app))
    result = client.call('POST', '/shop/orders', order_body(catalogue, **change))
    assert result.status_code == 400, result.json
    assert result.json['error']['code'] == code
    with app.app_context():
        assert db.session.scalar(select(ShopOrder)) is None
        assert db.session.scalar(select(ShopOrderItem)) is None


def test_custom_photo_requires_explicit_authorisation_and_is_frozen(app, client):
    register(client)
    photo = upload(client)
    catalogue = product(administrator(app), photoRequired=True)
    assert client.call('POST', '/shop/orders', order_body(catalogue)).status_code == 400
    assert client.call('POST', '/shop/orders', order_body(catalogue, photoUri=photo)).status_code == 400
    result = client.call('POST', '/shop/orders', order_body(catalogue, photoUri=photo, authorisePhoto=True))
    assert result.status_code == 201, result.json
    with app.app_context():
        item = db.session.scalar(select(ShopOrderItem))
        assert item.photo_data == image_bytes() and item.snapshot['photoAuthorised']


def test_memoir_purchase_requires_own_ready_revision_and_active_variant(app, client):
    register(client)
    memoir, _ = draft(client)
    admin = administrator(app)
    catalogue = product(admin, 'memoir_digital')
    submitted = submit(client, memoir)
    assert client.call('POST', '/shop/orders', order_body(catalogue, revisionId=submitted['revisionId'])).status_code == 400
    claimed = action(admin, submitted, 'claim').json['data']
    approved = action(admin, claimed, 'review', decision='approve').json['data']
    ready = action(admin, approved, 'generate').json['data']
    stranger = Client(app)
    register(stranger, 'stranger@example.test')
    assert stranger.call('POST', '/shop/orders', order_body(catalogue, revisionId=ready['revisionId'])).status_code == 400
    assert client.call('POST', '/shop/orders', order_body(catalogue, revisionId=ready['revisionId'])).status_code == 201
    catalogue['active'] = False
    assert admin.call('PUT', '/admin/products/'+catalogue['id'], catalogue).status_code == 200
    assert client.call('GET', '/shop/products').json['data']['products'] == []
    assert client.call('POST', '/shop/orders', order_body(catalogue, revisionId=ready['revisionId'])).status_code == 409


def test_additive_migration_preserves_existing_sources_photos_and_drafts():
    from app import create_app
    application = create_app({'SQLALCHEMY_DATABASE_URI': 'sqlite://'})
    runner = application.test_cli_runner()
    assert runner.invoke(args=['db', 'upgrade', '20261020_remove_legacy']).exit_code == 0
    # 在新账户结构上线前建立旧空间/记录，模拟真实升级而非仅测试空库。
    from app.models import LocalSpace, Draft
    with application.app_context():
        space = LocalSpace()
        db.session.add(space)
        db.session.flush()
        record = LifeRecord(user_id=space.id, title='升级前的记录', content='不能丢失', record_state='occurred', payload={})
        photo = Photo(user_id=space.id, content_type='image/png', data=image_bytes())
        draft_row = Draft(owner_id=space.id, kind='record', payload={'title': '未完成草稿'})
        db.session.add_all([record, photo, draft_row])
        db.session.commit()
        ids = record.id, photo.id, draft_row.id
    result = runner.invoke(args=['db', 'upgrade'])
    assert result.exit_code == 0, result.output
    checked = runner.invoke(args=['db', 'check'])
    assert checked.exit_code == 0, checked.output
    with application.app_context():
        assert db.session.get(LifeRecord, ids[0]).content == '不能丢失'
        assert db.session.get(Photo, ids[1]).data == image_bytes()
        assert db.session.get(Draft, ids[2]).payload['title'] == '未完成草稿'
        db.session.remove()
        db.engine.dispose()
