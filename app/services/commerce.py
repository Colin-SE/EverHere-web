"""交易状态的可信入口、限量库存和履约门槛。"""
from collections import Counter
from datetime import timedelta
from hashlib import sha256
from uuid import uuid4

from flask import current_app
from sqlalchemy import select

from ..extensions import db
from ..models import now
from ..models_trade import OrderTrade, TradeEvent
from ..models_workflow import ProductVariant, ShopOrder, ShopOrderItem
from ..security import APIError
from .alipay import AlipayError, amount_cents, cents_amount
from .records import text

PAYMENT_WINDOW = timedelta(minutes=30)
PAID = {'TRADE_SUCCESS', 'TRADE_FINISHED'}
ELECTRONIC = 'memoir_digital'


def gateway(required=True):
    client = current_app.extensions.get('everhere_alipay')
    if required and client is None:
        raise APIError('支付宝尚未配置。', 503, 'payment_unavailable')
    return client


def locked_order(order_id):
    order = db.session.scalar(select(ShopOrder).where(ShopOrder.id == order_id).with_for_update()
                              .execution_options(populate_existing=True))
    if not order:
        raise APIError('订单不存在。', 404, 'not_found')
    return order


def order_items(order_id):
    return list(db.session.scalars(select(ShopOrderItem).where(ShopOrderItem.order_id == order_id)))


def locked_trade(order_id):
    return db.session.scalar(select(OrderTrade).where(OrderTrade.order_id == order_id).with_for_update()
                             .execution_options(populate_existing=True))


def has_physical(items):
    return any(item.snapshot['kind'] != ELECTRONIC for item in items)


def shipping_address(raw):
    if not isinstance(raw, dict):
        raise APIError('请填写实体商品的收货地址。', code='address')
    names = {'recipient': ('收件人', 60), 'phone': ('收货联系电话', 30),
             'region': ('收货地区', 150), 'detail': ('详细地址', 300)}
    address = {key: text(raw.get(key), label, limit) for key, (label, limit) in names.items()}
    if not all(address.values()) or sum(char.isdigit() for char in address['phone']) < 7:
        raise APIError('请填写完整的收货地址和联系电话。', code='address')
    return address


def confirm_context(trade, client):
    if (trade.app_id, trade.seller_id, trade.environment) != (client.app_id, client.seller_id, client.environment):
        raise APIError('此订单属于不同的支付宝配置，请联系管理员核对。', 409, 'payment_environment')


def event(order, kind, actor=None, key=None):
    key = key or kind
    existing = db.session.scalar(select(TradeEvent.id).where(
        TradeEvent.order_id == order.id, TradeEvent.event_key == key).with_for_update())
    if existing:
        return False
    db.session.add(TradeEvent(order_id=order.id, event_key=key, kind=kind, actor_id=actor))
    return True


def variants(ids):
    return {row.id: row for row in db.session.scalars(select(ProductVariant)
            .where(ProductVariant.id.in_(ids)).order_by(ProductVariant.id).with_for_update()
            .execution_options(populate_existing=True))}


def reserve(items):
    quantities = Counter()
    for item in items:
        quantities[item.variant_id] += item.quantity
    reserved = {}
    for id, variant in variants(quantities).items():
        if variant.stock_available is not None:
            quantity = quantities[id]
            if variant.stock_available < quantity:
                raise APIError('库存不足，请重新选择商品数量。', 409, 'stock_unavailable')
            variant.stock_available -= quantity
            reserved[id] = quantity
    return reserved


def release(trade):
    if trade.stock_released:
        return
    for id, variant in variants(trade.stock).items():
        if variant.stock_available is not None:
            variant.stock_available += trade.stock[id]
    trade.stock_released = True


def start(order, raw_address, actor):
    client = gateway()
    trade = locked_trade(order.id)
    if trade:
        confirm_context(trade, client)
        if order.state != 'confirming' or trade.expires_at <= now():
            raise APIError('付款状态待核实，请先查询原订单。', 409, 'payment_check')
    else:
        if order.state != 'unpaid' or order.processing_state == 'cancelled':
            raise APIError('当前订单无法支付。', 409, 'invalid_payment_state')
        items = order_items(order.id)
        address = shipping_address(raw_address) if has_physical(items) else None
        # 支付宝链接与 MySQL DATETIME 都使用秒，首次签名与重试必须一致。
        expiry = (now() + PAYMENT_WINDOW).replace(microsecond=0)
        trade = OrderTrade(order_id=order.id, merchant_no=uuid4().hex, app_id=client.app_id,
                           seller_id=client.seller_id, environment=client.environment, amount_cents=order.total_cents,
                           expires_at=expiry, address=address, stock=reserve(items))
        db.session.add(trade)
        order.state = 'confirming'
        event(order, 'checkout', actor)
    link = client.checkout_url(trade)
    db.session.commit()
    return link


def validate_transaction(trade, result):
    status = result.get('trade_status')
    reference = result.get('trade_no')
    if (result.get('out_trade_no') != trade.merchant_no or amount_cents(result.get('total_amount')) != trade.amount_cents
            or (result.get('trans_currency') or 'CNY') != 'CNY'
            or not isinstance(reference, str) or not reference.isascii() or not reference.isdigit() or len(reference) > 64
            or (trade.provider_no and trade.provider_no != reference)
            or status not in PAID | {'WAIT_BUYER_PAY', 'TRADE_CLOSED'}):
        raise AlipayError('transaction_mismatch')
    return status, reference


def apply_alipay(order, trade, result):
    status, reference = validate_transaction(trade, result)
    trade.provider_no = reference
    if status in PAID:
        if trade.paid_at:
            return
        trade.paid_at = now()
        if order.state in ('closed', 'closing'):
            order.state = 'review'
            release(trade)
            event(order, 'late_payment')
        elif order.state == 'confirming':
            order.state = 'paid'
            if not has_physical(order_items(order.id)):
                trade.fulfillment = 'delivered'
            event(order, 'paid')
    elif status == 'TRADE_CLOSED' and order.state in ('confirming', 'closing') and not trade.paid_at:
        order.state = 'closed'
        release(trade)
        event(order, 'closed')
    trade.updated_at = now()


def receive(fields):
    client = gateway()
    client.verify_notice(fields)
    notice_id = fields.get('notify_id', '')
    if not 1 <= len(notice_id) <= 128 or fields.get('notify_type') != 'trade_status_sync':
        raise AlipayError('unexpected_notice')
    order_id = db.session.scalar(select(OrderTrade.order_id).where(OrderTrade.merchant_no == fields.get('out_trade_no')))
    order = locked_order(order_id)
    trade = locked_trade(order.id)
    confirm_context(trade, client)
    if fields.get('app_id') != trade.app_id or fields.get('seller_id') != trade.seller_id:
        raise AlipayError('merchant_mismatch')
    validate_transaction(trade, fields)
    key = 'notify:' + sha256(notice_id.encode()).hexdigest()
    if event(order, 'alipay_notice', key=key):
        apply_alipay(order, trade, fields)
    db.session.commit()


def query_trade(order, trade, client):
    confirm_context(trade, client)
    lookup = {'out_trade_no': trade.merchant_no}
    return client.call('alipay.trade.query', lookup)


def refresh(order):
    client = gateway()
    trade = locked_trade(order.id)
    if not trade:
        return
    if trade.refund_state in ('sending', 'uncertain'):
        query_refund(order, trade, client)
    elif order.state in ('confirming', 'closing', 'closed', 'review'):
        result = query_trade(order, trade, client)
        if result.get('code') == '10000':
            apply_alipay(order, trade, result)
        elif result.get('sub_code') != 'ACQ.TRADE_NOT_EXIST':
            raise AlipayError('unknown_payment')
    db.session.commit()


def close(order, actor=None, expired_only=False):
    trade = locked_trade(order.id)
    if order.state == 'closed':
        return
    if order.state == 'unpaid' and not expired_only:
        order.state = 'closed'
        event(order, 'closed', actor)
        db.session.commit()
        return
    if not trade or order.state not in ('confirming', 'closing'):
        raise APIError('只有未支付订单可以关闭。', 409, 'invalid_payment_state')
    if expired_only and now() < trade.expires_at:
        return
    client = gateway()
    result = query_trade(order, trade, client)
    if result.get('code') == '10000':
        apply_alipay(order, trade, result)
        if order.state in ('paid', 'closed', 'review'):
            db.session.commit()
            return
    elif result.get('sub_code') != 'ACQ.TRADE_NOT_EXIST':
        raise AlipayError('unknown_payment')
    # 未创建渠道单时仍可能有已生成的支付链接，仅在链接的绝对过期时间后释放库存。
    if result.get('sub_code') == 'ACQ.TRADE_NOT_EXIST' and now() < trade.expires_at:
        order.state = 'closing'
        event(order, 'closing', actor)
        db.session.commit()
        return
    if result.get('sub_code') != 'ACQ.TRADE_NOT_EXIST':
        result = client.call('alipay.trade.close', {'out_trade_no': trade.merchant_no})
        if (result.get('code') != '10000' or result.get('out_trade_no') != trade.merchant_no
                or result.get('trade_no') != trade.provider_no):
            raise AlipayError('close_unconfirmed')
    order.state = 'closed'
    release(trade)
    event(order, 'closed', actor)
    db.session.commit()


def request_refund(order, reason, actor):
    trade = locked_trade(order.id)
    if (not trade or order.state not in ('paid', 'review') or trade.fulfillment in ('shipped', 'received', 'started')):
        raise APIError('当前订单须由管理员核对，无法自动申请退款。', 409, 'refund_unavailable')
    if trade.refund_state:
        return
    reason = text(reason, '退款原因', 400)
    if not reason:
        raise APIError('请填写退款原因。', code='reason')
    trade.refund_no = uuid4().hex
    trade.refund_state, trade.refund_reason = 'requested', reason
    event(order, 'refund_requested', actor)
    db.session.commit()


def query_refund(order, trade, client):
    confirm_context(trade, client)
    result = client.call('alipay.trade.fastpay.refund.query', {
        'out_trade_no': trade.merchant_no, 'out_request_no': trade.refund_no,
    })
    if (result.get('code') == '10000' and result.get('refund_status') == 'REFUND_SUCCESS'
            and result.get('out_trade_no') == trade.merchant_no and result.get('out_request_no') == trade.refund_no
            and result.get('trade_no') == trade.provider_no
            and amount_cents(result.get('refund_amount')) == trade.amount_cents):
        trade.refund_state = 'refunded'
        order.state = 'refunded'
        release(trade)
        event(order, 'refunded')
        return True
    return False


def submit_refund(order, actor, retry=False):
    client = gateway()
    trade = locked_trade(order.id)
    if not trade or trade.refund_state not in ('requested', 'sending', 'uncertain', 'rejected', 'refunded'):
        raise APIError('退款申请不存在。', 409, 'invalid_refund_state')
    confirm_context(trade, client)
    if trade.refund_state == 'refunded':
        return
    if trade.refund_state != 'requested':
        if query_refund(order, trade, client):
            db.session.commit()
            return
        if not retry:
            return
    order.state = 'refunding'
    trade.refund_state = 'sending'
    event(order, 'refund_submitted', actor)
    order_id = order.id
    db.session.commit()

    order = locked_order(order_id)
    trade = locked_trade(order.id)
    if trade.refund_state == 'refunded':
        return
    try:
        result = client.call('alipay.trade.refund', {'out_trade_no': trade.merchant_no,
                             'out_request_no': trade.refund_no, 'refund_amount': cents_amount(trade.amount_cents),
                             'refund_reason': 'Everhere 订单全额退款'})
        if not query_refund(order, trade, client):
            trade.refund_state = 'uncertain' if result.get('code') in ('10000', '20000') else 'rejected'
            event(order, 'refund_check_needed')
    except AlipayError:
        trade.refund_state = 'uncertain'
        event(order, 'refund_check_needed')
    db.session.commit()


def fulfill(order, action, fields, actor):
    trade = locked_trade(order.id)
    if (not trade or order.state != 'paid' or trade.refund_state or not trade.address):
        raise APIError('订单未满足实体履约条件。', 409, 'invalid_fulfillment')
    transitions = {'start': ('pending', 'started'), 'ship': ('started', 'shipped'), 'receive': ('shipped', 'received')}
    previous, target = transitions[action]
    if trade.fulfillment == target:
        return
    if trade.fulfillment != previous:
        raise APIError('订单的履约阶段已变化。', 409, 'invalid_fulfillment')
    if action == 'ship':
        trade.carrier = text(fields.get('carrier'), '物流公司', 80)
        trade.tracking = text(fields.get('tracking'), '物流单号', 100)
        if not trade.carrier or not trade.tracking:
            raise APIError('请填写物流公司和物流单号。', code='tracking')
    trade.fulfillment = target
    event(order, target, actor)
    db.session.commit()


def expire_overdue(limit=25):
    pending = list(db.session.scalars(select(OrderTrade.order_id).join(ShopOrder)
        .where(ShopOrder.state.in_(['confirming', 'closing']), OrderTrade.expires_at <= now())
        .order_by(OrderTrade.updated_at, OrderTrade.expires_at).limit(limit)))
    db.session.rollback()
    failed = 0
    for order_id in pending:
        try:
            close(locked_order(order_id), expired_only=True)
        except (AlipayError, APIError):
            db.session.rollback()
            locked_order(order_id)
            trade = locked_trade(order_id)
            trade.updated_at = now()
            db.session.commit()
            failed += 1
        finally:
            db.session.remove()
    return len(pending), failed
