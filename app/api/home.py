from flask import Blueprint, g
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from ..extensions import db
from ..models import LifeRecord
from ..models_workflow import Memoir, ShopOrder
from ..security import member_required
from ..services.records import record_data

bp = Blueprint('home', __name__, url_prefix='/api/v1/home')


@bp.get('/album')
def album():
    visible = select(LifeRecord).where(LifeRecord.user_id == g.owner.id, LifeRecord.is_deleted.is_(False))
    total = db.session.scalar(select(func.count()).select_from(visible.subquery()))
    ongoing = visible.where(LifeRecord.record_state == 'ongoing')
    plans = visible.where(LifeRecord.record_state == 'planned',
                          LifeRecord.payload['completionState'].as_string().not_in(['completed', 'cancelled']))

    def count(query):
        return db.session.scalar(select(func.count()).select_from(query.subquery()))

    def read(query, order, limit):
        rows = db.session.scalars(query.order_by(order, LifeRecord.source_id).limit(limit)
                                 .options(selectinload(LifeRecord.links)))
        return [record_data(row) for row in rows]

    return {'data': {'total': total, 'ongoing': count(ongoing), 'planned': count(plans),
                     'records': read(visible, LifeRecord.updated_at.desc(), 3),
                     'ongoingRecords': read(ongoing, LifeRecord.updated_at.desc(), 2),
                     'plans': read(plans.order_by(LifeRecord.event_date.is_(None)), LifeRecord.event_date, 2)}}


@bp.get('/summary')
@member_required
def summary():
    active_memoirs = select(func.count()).select_from(Memoir).where(
        Memoir.owner_id == g.member.id, Memoir.state.in_(['draft', 'returned', 'submitted', 'approved']))
    active_orders = select(func.count()).select_from(ShopOrder).where(
        ShopOrder.buyer_id == g.member.id, ShopOrder.processing_state.in_(['pending', 'processing', 'needs_info']))
    return {'data': {'memoirs': db.session.scalar(active_memoirs), 'orders': db.session.scalar(active_orders)}}
