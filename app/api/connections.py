"""只查询当前空间中已保存的人物与记录关联。"""
from flask import Blueprint, g, request
from sqlalchemy import exists, func, select

from ..extensions import db
from ..models import LifeNode, LifeRecord, RecordNode
from ..security import APIError, local_required, page_number

bp = Blueprint('connections', __name__, url_prefix='/api/v1/connections')
PAGE_SIZE = 16


def people():
    return select(LifeNode).where(LifeNode.user_id == g.owner.id, LifeNode.is_deleted.is_(False),
                                  LifeNode.kind == 'entities', func.coalesce(LifeNode.payload['type'].as_string(), 'person') == 'person')


def records():
    return select(LifeRecord).where(LifeRecord.user_id == g.owner.id, LifeRecord.is_deleted.is_(False))


def person_data(person):
    return {'id': person.source_id, 'kind': 'person', 'label': person.name}


def record_data(record):
    return {'id': record.source_id, 'kind': 'record', 'label': record.title,
            'date': record.payload.get('eventDate')}


@bp.get('')
@local_required
def explore():
    kind = request.args.get('kind', 'person')
    if kind not in ('person', 'record'):
        raise APIError('关系类型无效。', code='kind')
    page = page_number()
    focus = None
    identifier = request.args.get('id')
    query = people() if kind == 'person' else records()
    if identifier:
        model = LifeNode if kind == 'person' else LifeRecord
        row = db.session.scalar(query.where(model.source_id == identifier))
        if not row:
            raise APIError('记录或人物已不可用。', 404, 'not_found')
        focus = (person_data if kind == 'person' else record_data)(row)
        if kind == 'person':
            query = records().where(exists().where(RecordNode.record_id == LifeRecord.id, RecordNode.node_id == row.id))
        else:
            query = people().where(exists().where(RecordNode.record_id == row.id, RecordNode.node_id == LifeNode.id))
        kind = 'record' if kind == 'person' else 'person'
    term = request.args.get('q', '').strip()[:120]
    if kind == 'person':
        if term:
            query = query.where(LifeNode.name.contains(term, autoescape=True))
        query = query.order_by(LifeNode.name, LifeNode.id)
    else:
        if term:
            query = query.where(LifeRecord.title.contains(term, autoescape=True))
        query = query.order_by(LifeRecord.updated_at.desc(), LifeRecord.id)
    rows = list(db.session.scalars(query.offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE + 1)))
    serialize = person_data if kind == 'person' else record_data
    return {'data': {'focus': focus, 'nodes': [serialize(row) for row in rows[:PAGE_SIZE]],
                     'page': page, 'hasMore': len(rows) > PAGE_SIZE,
                     'source': 'record_association' if focus else None}}
