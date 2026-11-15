"""按本人或受分配人员授权读取订单和处理记录。"""
from io import BytesIO

from flask import Blueprint, g, send_file
from sqlalchemy import select

from ..extensions import db
from ..models_workflow import Member, ShopOrder, ShopOrderItem
from ..security import APIError, admin_required, body, member_required
from ..services.orders import change_order, order_data, order_page

bp = Blueprint('order_processing', __name__, url_prefix='/api/v1')


@bp.get('/shop/orders/by-request/<key>')
@member_required
def by_request(key):
    order = db.session.scalar(select(ShopOrder).where(ShopOrder.buyer_id == g.member.id, ShopOrder.request_key == key))
    if not order:
        raise APIError('订单不存在。', 404, 'not_found')
    return {'data': order_data(order)}


@bp.post('/shop/orders/<order_id>/reply')
@member_required
def reply(order_id):
    return {'data': order_data(change_order(order_id, {**body(), 'action': 'reply'}))}


@bp.get('/admin/orders')
@admin_required
def queue():
    return {'data': order_page(select(ShopOrder).join(Member, Member.id == ShopOrder.buyer_id), staff=True)}


@bp.get('/admin/orders/<order_id>')
@admin_required
def detail(order_id):
    order = db.session.get(ShopOrder, order_id)
    if not order:
        raise APIError('订单不存在。', 404, 'not_found')
    return {'data': order_data(order, staff=True)}


@bp.post('/admin/orders/<order_id>/process')
@admin_required
def process(order_id):
    return {'data': order_data(change_order(order_id, body(), staff=True), staff=True)}


@bp.get('/admin/orders/<order_id>/photos/<item_id>')
@admin_required
def photo(order_id, item_id):
    order = db.session.get(ShopOrder, order_id)
    item = db.session.get(ShopOrderItem, item_id)
    if (not order or not item or item.order_id != order_id or order.assignee_id != g.member.id
            or order.buyer_id == g.member.id or not item.photo_type):
        raise APIError('照片不存在。', 404, 'not_found')
    return send_file(BytesIO(item.photo_data), mimetype=item.photo_type, max_age=0)
