"""隔离网关状态机和 RSA2 协议测试，无真实支付宝或正式数据库连接。"""
from base64 import b64decode, b64encode
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json
from urllib.parse import parse_qs, urlsplit
from threading import Barrier
from uuid import uuid4

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
import pytest
from sqlalchemy import select

from app.extensions import db
from app.models import now
from app.models_trade import OrderTrade, TradeEvent
from app.models_workflow import ProductVariant, ShopOrder
from app.services.alipay import Alipay, AlipayError, payload, signed_member
from app.services.alipay_reconciliation import compare_bill
from app.services.commerce import expire_overdue
from conftest import Client
from test_workflows import action, administrator, draft, order_body, product, register, submit

ADDRESS = {'recipient': '测试收件人', 'phone': '13800000000', 'region': '测试省测试市', 'detail': '沙箱门牌90号'}
PROVIDER_NO = '20261115000000000001'


class FixtureGateway:
    environment = 'sandbox'
    app_id = '2026111500000001'
    seller_id = '2088000000000001'

    def __init__(self, protocol):
        self.protocol = protocol
        self.responses = {}
        self.calls = []

    def checkout_url(self, trade):
        return self.protocol.checkout_url(trade)

    def verify_notice(self, fields):
        return self.protocol.verify_notice(fields)

    def call(self, method, biz):
        self.calls.append((method, biz))
        value = self.responses[method]
        if isinstance(value, Exception):
            raise value
        return value(biz) if callable(value) else value


@pytest.fixture
def merchant(app, tmp_path):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    provider = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private = tmp_path / 'synthetic-private.pem'
    public = tmp_path / 'synthetic-alipay-public.pem'
    private.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    public.write_bytes(provider.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    protocol = Alipay({'ALIPAY_MODE': 'sandbox', 'ALIPAY_APP_ID': FixtureGateway.app_id, 'ALIPAY_SELLER_ID': FixtureGateway.seller_id,
                       'ALIPAY_PUBLIC_ORIGIN': 'https://sandbox.example.test',
                       'ALIPAY_PRIVATE_KEY_FILE': str(private), 'ALIPAY_PUBLIC_KEY_FILE': str(public)})
    fixture = FixtureGateway(protocol)
    fixture.provider = provider
    fixture.application = key
    app.extensions['everhere_alipay'] = fixture
    return fixture


def add_order(client, item, **changes):
    response = client.call('POST', '/shop/orders', order_body(item, **changes))
    assert response.status_code == 201, response.json
    return response.json['data']


def checkout(client, order, address=ADDRESS):
    return client.call('POST', '/shop/orders/' + order['id'] + '/alipay', {'address': address})


def signed_notice(merchant, merchant_no, *, status='TRADE_SUCCESS', notify_id=None, **changes):
    fields = {'app_id': merchant.app_id, 'seller_id': merchant.seller_id, 'total_amount': '78.00',
              'out_trade_no': merchant_no, 'trade_no': PROVIDER_NO, 'trade_status': status,
              'notify_id': notify_id or uuid4().hex, 'sign_type': 'RSA2', 'notify_type': 'trade_status_sync', **changes}
    fields['sign'] = b64encode(merchant.provider.sign(payload(fields, ('sign', 'sign_type')), padding.PKCS1v15(), hashes.SHA256())).decode()
    return fields


def entry(response):
    assert response.status_code == 200, response.json
    query = {k: values[0] for k, values in parse_qs(urlsplit(response.json['data']['checkoutUrl']).query).items()}
    return query, json.loads(query['biz_content'])


def claim(admin, order):
    path = '/admin/orders/' + order['id']
    value = admin.call('POST', path + '/process', {'version': order['version'], 'action': 'claim'})
    assert value.status_code == 200, value.json
    return path


def test_rsa2_signed_envelope_and_original_json(merchant):
    original = '{ "trade_status" : "WAIT_BUYER_PAY", "total_amount":78.00 }'
    sig = b64encode(merchant.provider.sign(original.encode(), padding.PKCS1v15(), hashes.SHA256())).decode()
    (obj, raw), proof = signed_member('{"alipay_trade_query_response":' + original + ',"sign":"' + sig + '"}', 'alipay_trade_query_response')
    assert raw == original and obj['trade_status'] == 'WAIT_BUYER_PAY'
    merchant.protocol.verify(raw.encode(), proof)
    with pytest.raises(AlipayError):
        merchant.protocol.verify(raw.replace('78','79').encode(), proof)


def test_physical_checkout_callback_idempotency_and_fulfillment(app, client, merchant, monkeypatch):
    from app.services import commerce
    stamp = now().replace(microsecond=950_000)
    monkeypatch.setattr(commerce, 'now', lambda: stamp)
    register(client)
    admin = administrator(app)
    item = product(admin)
    order = add_order(client, item)
    own = '/shop/orders/' + order['id']
    assert checkout(client, order, None).status_code == 400
    params, signed = entry(checkout(client, order))
    assert signed['total_amount'] == '78.00' and signed['product_code'] == 'FAST_INSTANT_TRADE_PAY'
    assert params['notify_url'].endswith('/payments/alipay/notify')
    merchant.application.public_key().verify(b64decode(params['sign']),
                                              payload(params, ('sign',)), padding.PKCS1v15(), hashes.SHA256())
    _, other = entry(checkout(client, order, {**ADDRESS, 'detail': '不得改写'}))
    assert other == signed
    foreign = Client(app)
    register(foreign, 'foreign@example.test')
    assert checkout(foreign, order).status_code == 404
    assert client.call('GET', own).json['data']['state'] == 'confirming'
    callback = '/payments/alipay/notify'
    assert client.client.post(callback, data=signed_notice(merchant, signed['out_trade_no'], seller_id='2088000000000002')).status_code == 400
    assert client.client.post(callback, data=signed_notice(merchant, signed['out_trade_no'], total_amount='0.01')).status_code == 400
    assert client.client.post(callback, data={**signed_notice(merchant, signed['out_trade_no']), 'trade_status': 'TRADE_CLOSED'}).status_code == 400
    assert client.client.get('/orders/' + order['id'] + '?trade_status=TRADE_SUCCESS').status_code == 200
    assert client.call('GET', own).json['data']['state'] == 'confirming'

    good = signed_notice(merchant, signed['out_trade_no'])
    assert client.client.post(callback, data=good).data == b'success'
    assert client.client.post(callback, data=good).data == b'success'
    assert client.client.post(callback, data=signed_notice(merchant, signed['out_trade_no'])).data == b'success'
    assert client.call('GET', own).json['data']['trade']['address']['detail'] == ADDRESS['detail']
    admin_path = '/admin/orders/' + order['id']
    assert 'trade' not in admin.call('GET', admin_path).json['data']
    claim(admin, order)
    assert admin.call('POST', admin_path + '/fulfillment', {'action': 'start'}).status_code == 200
    assert client.call('POST', own + '/refund', {'reason': '制作后测试'}).status_code == 409
    assert admin.call('POST', admin_path + '/fulfillment', {'action': 'ship', 'carrier': '测试物流','tracking': 'F001'}).status_code == 200
    assert client.call('POST', own + '/receive', {}).json['data']['trade']['fulfillment'] == 'received'
    with app.app_context():
        assert db.session.query(TradeEvent).filter_by(order_id=order['id'], kind='paid').count() == 1


def test_expiry_releases_once_and_late_payment_never_delivers(app, client, merchant):
    register(client)
    admin = administrator(app)
    item = product(admin, stockAvailable=2)
    order = add_order(client, item)
    _, signed = entry(checkout(client, order))
    merchant.responses['alipay.trade.query'] = {'code': '40004', 'sub_code': 'ACQ.TRADE_NOT_EXIST'}
    other = add_order(client, item)
    assert checkout(client, other).json['error']['code'] == 'stock_unavailable'
    own = '/shop/orders/' + order['id']
    assert client.call('POST', own + '/cancel', {}).json['data']['state'] == 'closing'
    with app.app_context():
        assert db.session.get(ProductVariant, item['variants'][0]['id']).stock_available == 0
        trade = db.session.get(OrderTrade, order['id'])
        trade.expires_at = now() - timedelta(seconds=1)
        db.session.commit()
        assert expire_overdue() == (1, 0)
        assert expire_overdue() == (0, 0)
        assert db.session.get(ProductVariant, item['variants'][0]['id']).stock_available == 2
    assert client.client.post('/payments/alipay/notify', data=signed_notice(merchant, signed['out_trade_no'])).status_code == 200
    assert client.call('GET', own).json['data']['state'] == 'review'
    claim(admin, order)
    assert admin.call('POST', '/admin/orders/' + order['id'] + '/fulfillment', {'action':'start'}).status_code == 409


def test_refund_failure_reuses_reference_and_revokes_electronic_access(app, client, merchant):
    register(client)
    admin = administrator(app)
    memoir, _ = draft(client)
    submitted = submit(client, memoir)
    accepted = action(admin, action(admin, submitted, 'claim').json['data'], 'review', decision='approve').json['data']
    ready = action(admin, accepted, 'generate').json['data']
    item = product(admin, kind='memoir_digital')
    order = add_order(client, item, revisionId=ready['revisionId'])
    own = '/shop/orders/' + order['id']
    download = own + '/items/' + order['items'][0]['id'] + '/download'
    assert client.call('GET', download).status_code == 404
    _, signed = entry(checkout(client, order, None))
    merchant_no = signed['out_trade_no']
    merchant.responses['alipay.trade.query'] = {'code': '10000', 'trade_status': 'TRADE_SUCCESS',
        'out_trade_no': merchant_no, 'trade_no': PROVIDER_NO, 'total_amount':'78.00'}
    assert client.call('POST', own+'/payment-status', {}).json['data']['state'] == 'paid'
    assert client.call('GET', download).data.startswith(b'%PDF')
    outsider = Client(app)
    register(outsider, 'outsider@example.test')
    assert outsider.call('GET', download).status_code == 404
    admin_path = claim(admin, order)
    refund = client.call('POST', own+'/refund', {'reason':'沙箱全额退款'})
    assert refund.json['data']['trade']['refundState'] == 'requested'
    assert client.call('GET', download).status_code == 404
    merchant.responses['alipay.trade.refund'] = AlipayError('timeout')
    merchant.responses['alipay.trade.fastpay.refund.query'] = {'code':'10000'}
    failed = admin.call('POST', admin_path + '/refund', {}).json['data']
    assert failed['state'] == 'refunding' and failed['trade']['refundState'] == 'uncertain'
    merchant.responses['alipay.trade.refund'] = {'code':'10000'}
    def after_retry(biz):
        if sum(name == 'alipay.trade.refund' for name, _ in merchant.calls) < 2:
            return {'code': '10000'}
        return {'code':'10000', 'trade_no':PROVIDER_NO, 'refund_status':'REFUND_SUCCESS',
                'out_trade_no':merchant_no, 'out_request_no':biz['out_request_no'], 'refund_amount':'78.00'}
    merchant.responses['alipay.trade.fastpay.refund.query'] = after_retry
    done = admin.call('POST', admin_path + '/refund', {'retry':True}).json['data']
    assert done['state'] == 'refunded'
    refund_attempts = [biz for name,biz in merchant.calls if name=='alipay.trade.refund']
    assert len(refund_attempts) == 2 and len({attempt['out_request_no'] for attempt in refund_attempts}) == 1
    assert client.call('GET', download).status_code == 404
    assert admin.call('POST', admin_path + '/refund', {'retry':True}).json['data']['state'] == 'refunded'

    batch = refund_attempts[0]['out_request_no']
    with app.app_context():
        day = db.session.scalar(select(TradeEvent).where(TradeEvent.kind=='paid')).created_at + timedelta(hours=8)
        heading = '支付宝交易号,商户订单号,业务类型,订单金额（元）,退款批次号\n'
        bill = heading + f'{PROVIDER_NO},{merchant_no},交易,78.00,\n{PROVIDER_NO},{merchant_no},退款,-78.00,{batch}\n'
        assert compare_bill(bill.encode(), day.date(), merchant) == (Counter(), Counter())
        missing, extra = compare_bill(bill.replace('-78.00','-77.00').encode(), day.date(), merchant)
        assert len(missing)==len(extra)==1
        assert db.session.get(ShopOrder, order['id']).state == 'refunded'


def test_two_devices_on_mysql_share_one_trade_and_one_stock_reservation(app, client, merchant):
    with app.app_context():
        if db.engine.dialect.name != 'mysql':
            pytest.skip('Requires MySQL row locks')
    register(client)
    second_device = Client(app)
    assert second_device.call('POST', '/accounts/login', {
        'email': 'owner@example.test', 'password': 'test-password-123',
    }).status_code == 200
    item = product(administrator(app), stockAvailable=2)
    order = add_order(client, item)
    barrier = Barrier(2, timeout=10)

    def pay(device):
        barrier.wait()
        return entry(checkout(device, order))[1]['out_trade_no']

    with ThreadPoolExecutor(max_workers=2) as pool:
        merchant_nos = list(pool.map(pay, (client, second_device)))
    assert len(set(merchant_nos)) == 1
    with app.app_context():
        assert db.session.query(OrderTrade).filter_by(order_id=order['id']).count() == 1
        assert db.session.get(ProductVariant, item['variants'][0]['id']).stock_available == 0
