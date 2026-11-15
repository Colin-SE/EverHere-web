"""订单处理与支付状态独立，所有变更与审计记录同事务提交。"""
from datetime import date, timedelta

from flask import g, request
from sqlalchemy import func, select

from ..extensions import db
from ..models import now
from ..models_workflow import Member, OrderEvent, ShopOrder, ShopOrderItem
from ..security import APIError, page_number
from .records import date_value, text

STATES = ('pending', 'processing', 'needs_info', 'completed', 'cancelled')
TRANSITIONS = {
    'claim': ('pending', 'processing'),
    'request_info': ('processing', 'needs_info'),
    'reply': ('needs_info', 'processing'),
    'complete': ('processing', 'completed'),
    'cancel': (('processing', 'needs_info'), 'cancelled'),
    'reopen': (('completed', 'cancelled'), 'processing'),
}
MAX_PAGE_SIZE = 25


def order_data(order, *, staff=False, detail=True):
    data = {
        'id': order.id, 'state': order.state, 'processingState': order.processing_state,
        'version': order.version, 'totalCents': order.total_cents,
        'createdAt': order.created_at.isoformat() + 'Z',
        'updatedAt': (order.updated_at or order.created_at).isoformat() + 'Z',
        'paymentAvailable': False,
    }
    items = db.session.scalars(select(ShopOrderItem).where(ShopOrderItem.order_id == order.id).order_by(ShopOrderItem.id))
    can_handle = staff and order.assignee_id == g.member.id and order.buyer_id != g.member.id
    data['items'] = [{
        'id': i.id, 'quantity': i.quantity, 'unitPriceCents': i.unit_price_cents,
        'snapshot': i.snapshot if not staff or can_handle else {
            key: i.snapshot[key] for key in ('productName', 'variantName', 'kind', 'currency')
        },
        **({'photoUrl': f'/api/v1/admin/orders/{order.id}/photos/{i.id}'} if can_handle and i.photo_type else {}),
    } for i in items]
    if staff:
        buyer = db.session.get(Member, order.buyer_id)
        assignee = db.session.get(Member, order.assignee_id) if order.assignee_id else None
        data.update(buyer={'id': buyer.id, 'name': buyer.name, 'email': buyer.email},
                    assignee=assignee.name if assignee else None, canHandle=can_handle,
                    canClaim=order.processing_state == 'pending' and order.buyer_id != g.member.id)
    if detail and (not staff or can_handle):
        query = select(OrderEvent).where(OrderEvent.order_id == order.id).order_by(OrderEvent.version)
        if not staff:
            query = query.where(OrderEvent.visible.is_(True))
        data['events'] = [{
            'action': event.action, 'state': event.state, 'message': event.message,
            'createdAt': event.created_at.isoformat() + 'Z',
            **({'actorId': event.actor_id, 'visible': event.visible} if staff else {}),
        } for event in db.session.scalars(query)]
    return data


def order_page(query, *, staff=False):
    status = request.args.get('status', '')
    if status:
        statuses = {'unresolved': STATES[:3], 'resolved': STATES[3:]}.get(status, (status,))
        if any(value not in STATES for value in statuses):
            raise APIError('订单处理状态无效。', code='status')
        query = query.where(ShopOrder.processing_state.in_(statuses))
    if staff:
        term = request.args.get('q', '').strip()[:120]
        if term:
            query = query.where((ShopOrder.id.contains(term, autoescape=True)) |
                                (Member.name.contains(term, autoescape=True)) |
                                (Member.email.contains(term, autoescape=True)))
        if request.args.get('buyer'):
            query = query.where(ShopOrder.buyer_id == request.args['buyer'])
        if request.args.get('assigned') == 'me':
            query = query.where(ShopOrder.assignee_id == g.member.id)
        start = date_value(request.args.get('from'), '订单日期')
        end = date_value(request.args.get('to'), '订单日期')
        if start and end and start > end:
            raise APIError('筛选的截止日期不能早于起始日期。')
        if start:
            query = query.where(ShopOrder.created_at >= start)
        if end and end < date.max:
            query = query.where(ShopOrder.created_at < end + timedelta(days=1))
        kind = request.args.get('kind')
        if kind:
            if kind not in ('medal', 'gift', 'memoir_digital', 'memoir_paper'):
                raise APIError('商品类型无效。', code='kind')
            query = query.where(select(ShopOrderItem.id).where(
                ShopOrderItem.order_id == ShopOrder.id,
                ShopOrderItem.snapshot['kind'].as_string() == kind,
            ).exists())
    page = page_number()
    total = db.session.scalar(select(func.count()).select_from(query.subquery()))
    orders = db.session.scalars(query.order_by(ShopOrder.created_at.desc(), ShopOrder.id.desc())
                               .offset((page - 1) * MAX_PAGE_SIZE).limit(MAX_PAGE_SIZE))
    return {'orders': [order_data(order, staff=staff, detail=False) for order in orders],
            'page': page, 'pageSize': MAX_PAGE_SIZE, 'total': total}


def change_order(order_id, data, *, staff=False):
    order = db.session.scalar(select(ShopOrder).where(ShopOrder.id == order_id)
                              .with_for_update().execution_options(populate_existing=True))
    if not order or (not staff and order.buyer_id != g.member.id):
        raise APIError('订单不存在。', 404, 'not_found')
    action = data.get('action')
    if not isinstance(action, str) or action not in (set(TRANSITIONS) - {'reply'} | {'note', 'message'} if staff else {'reply'}):
        raise APIError('订单操作无效。', code='action')
    if staff and (order.buyer_id == g.member.id or (action != 'claim' and order.assignee_id != g.member.id)):
        raise APIError('只能处理自己领取的订单。', 403, 'not_assigned')
    message = text(data.get('message'), '订单说明', 2000)
    if action in ('request_info', 'reply', 'cancel', 'reopen', 'note', 'message') and not message:
        raise APIError('请填写订单说明。', code='message')
    expected = data.get('version')
    if type(expected) is not int or expected < 1:
        raise APIError('订单已更新，请重新读取后继续。', 409, 'version_conflict')
    if expected != order.version:
        event = db.session.scalar(select(OrderEvent).where(OrderEvent.order_id == order.id, OrderEvent.version == expected + 1))
        if event and event.actor_id == g.member.id and event.action == action and event.message == message:
            return order
        raise APIError('订单已更新，请重新读取后继续。', 409, 'version_conflict')
    next_state = order.processing_state
    if action in TRANSITIONS:
        allowed, next_state = TRANSITIONS[action]
        allowed = (allowed,) if isinstance(allowed, str) else allowed
        if order.processing_state not in allowed:
            raise APIError('当前订单状态无法执行此操作。', 409, 'invalid_state')
    # 条件更新也覆盖 SQLite 等不支持 SELECT FOR UPDATE 的隔离环境。
    stamp = now()
    values = {'processing_state': next_state, 'version': expected + 1, 'updated_at': stamp}
    if action == 'claim':
        values['assignee_id'] = g.member.id
    changed = db.session.execute(db.update(ShopOrder).where(ShopOrder.id == order.id, ShopOrder.version == expected)
                                 .values(**values))
    if changed.rowcount != 1:
        raise APIError('订单已更新，请重新读取后继续。', 409, 'version_conflict')
    db.session.add(OrderEvent(order_id=order.id, actor_id=g.member.id, version=expected + 1,
                             action=action, state=next_state, message=message, visible=action != 'note',
                             created_at=stamp))
    db.session.commit()
    return order
