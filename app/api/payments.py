"""支付宝回调、买家交易操作和受分配管理员的履约入口。"""
from io import BytesIO

from flask import Blueprint, Response, g, request, send_file
from sqlalchemy import select

from ..extensions import db, limiter
from ..i18n import translate
from ..models_trade import OrderTrade
from ..models_workflow import Memoir, MemoirAsset, MemoirRevision, ShopOrder, ShopOrderItem
from ..security import APIError, admin_required, body, member_required
from ..services import commerce
from ..services.alipay import AlipayError
from ..services.orders import order_data

bp = Blueprint('payments', __name__)


@bp.errorhandler(AlipayError)
def unknown(error):
    db.session.rollback()
    return {'error': {'message': translate('支付宝结果待核实，请查询原订单后继续。'),
                      'code': 'payment_unknown'}}, 503


def buyer_order(order_id):
    order = commerce.locked_order(order_id)
    if order.buyer_id != g.member.id:
        raise APIError('订单不存在。', 404, 'not_found')
    return order


def staff_order(order_id):
    order = commerce.locked_order(order_id)
    if order.assignee_id != g.member.id or order.buyer_id == g.member.id:
        raise APIError('只能处理自己领取的订单。', 403, 'not_assigned')
    return order


@bp.post('/payments/alipay/notify')
@limiter.limit('120 per minute')
def notice():
    request.max_content_length = 32768
    if request.mimetype != 'application/x-www-form-urlencoded':
        return Response('failure', status=400, mimetype='text/plain')
    fields = request.form
    if len(fields) > 100 or any(len(fields.getlist(key)) != 1 for key in fields):
        return Response('failure', status=400, mimetype='text/plain')
    try:
        commerce.receive(fields)
    except (AlipayError, APIError) as error:
        db.session.rollback()
        return Response('failure', status=503 if getattr(error, 'status', 400) == 503 else 400, mimetype='text/plain')
    return Response('success', mimetype='text/plain')


@bp.post('/api/v1/shop/orders/<order_id>/alipay')
@limiter.limit('20 per minute')
@member_required
def start(order_id):
    order = buyer_order(order_id)
    link = commerce.start(order, body().get('address'), g.member.id)
    return {'data': {'checkoutUrl': link}}


@bp.post('/api/v1/shop/orders/<order_id>/payment-status')
@limiter.limit('20 per minute')
@member_required
def refresh(order_id):
    order = buyer_order(order_id)
    commerce.refresh(order)
    return {'data': order_data(order)}


@bp.post('/api/v1/shop/orders/<order_id>/cancel')
@member_required
def cancel(order_id):
    commerce.gateway()
    order = buyer_order(order_id)
    commerce.close(order, g.member.id)
    return {'data': order_data(order)}


@bp.post('/api/v1/shop/orders/<order_id>/refund')
@member_required
def refund(order_id):
    commerce.gateway()
    order = buyer_order(order_id)
    commerce.request_refund(order, body().get('reason'), g.member.id)
    return {'data': order_data(order)}


@bp.post('/api/v1/admin/orders/<order_id>/refund')
@limiter.limit('10 per minute')
@admin_required
def process_refund(order_id):
    order = staff_order(order_id)
    if order.state == 'review':
        commerce.request_refund(order, '关闭后收到付款，原路退回。', g.member.id)
        order = staff_order(order_id)
    commerce.submit_refund(order, g.member.id, retry=body().get('retry') is True)
    order = db.session.get(ShopOrder, order_id)
    return {'data': order_data(order, staff=True)}


@bp.post('/api/v1/admin/orders/<order_id>/payment-status')
@limiter.limit('20 per minute')
@admin_required
def staff_refresh(order_id):
    order = staff_order(order_id)
    commerce.refresh(order)
    return {'data': order_data(order, staff=True)}


@bp.post('/api/v1/admin/orders/<order_id>/fulfillment')
@admin_required
def fulfill(order_id):
    order = staff_order(order_id)
    payload = body()
    action = payload.get('action')
    if action not in ('start', 'ship'):
        raise APIError('履约操作无效。', code='action')
    commerce.fulfill(order, action, payload, g.member.id)
    return {'data': order_data(order, staff=True)}


@bp.post('/api/v1/shop/orders/<order_id>/receive')
@member_required
def receive(order_id):
    order = buyer_order(order_id)
    commerce.fulfill(order, 'receive', {}, g.member.id)
    return {'data': order_data(order)}


@bp.get('/api/v1/shop/orders/<order_id>/items/<item_id>/download')
@member_required
def download(order_id, item_id):
    # 只按订单冻结的版本发放，旧样张路由继续只显示部分页面。
    order = db.session.get(ShopOrder, order_id)
    trade = db.session.get(OrderTrade, order_id)
    item = db.session.get(ShopOrderItem, item_id)
    if (not order or order.buyer_id != g.member.id or order.state != 'paid' or not trade or trade.refund_state
            or not item or item.order_id != order.id or item.snapshot.get('kind') != commerce.ELECTRONIC):
        raise APIError('下载不可用。', 404, 'not_found')
    revision = db.session.get(MemoirRevision, item.revision_id)
    memoir = db.session.get(Memoir, revision.memoir_id) if revision else None
    if not memoir or memoir.owner_id != g.member.id:
        raise APIError('下载不可用。', 404, 'not_found')
    asset = db.session.scalar(select(MemoirAsset).where(MemoirAsset.revision_id == item.revision_id, MemoirAsset.kind == 'final'))
    if not asset:
        raise APIError('下载不可用。', 404, 'not_found')
    return send_file(BytesIO(asset.data), mimetype='application/pdf', as_attachment=True, download_name='memoir.pdf', max_age=0)
