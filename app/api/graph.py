"""人物管理与原生关系读取：修订保护、同名独立、软删除只解除普通记录关系。"""
from copy import deepcopy

from flask import Blueprint, g
from sqlalchemy import select

from ..extensions import db
from ..models import Draft, LifeNode, LifeRecord, RecordNode, now
from ..security import APIError, body, local_required
from ..services.records import KINDS, node_data, normalize_node
from ..services.android_archive import millis, node_document, record_document

bp = Blueprint('graph', __name__, url_prefix='/api/v1')


def owned_node(kind, source_id):
    node = db.session.scalar(select(LifeNode).where(LifeNode.user_id == g.owner.id, LifeNode.kind == kind, LifeNode.source_id == source_id, LifeNode.is_deleted.is_(False)))
    if not node:
        raise APIError('人物或关联资料不存在。', 404)
    return node


def save_node(kind, raw, node=None, source_id=None):
    data = normalize_node(kind, raw)
    if node is None:
        node = LifeNode(user_id=g.owner.id, kind=kind, name=data['name'], payload=data, source_id=source_id)
        db.session.add(node)
        db.session.flush()
    else:
        original = deepcopy(node.payload.get('androidDocument'))
        node.name, node.payload, node.updated_at = data['name'], {**node.payload, **data}, now()
        node.version += 1
        if original:
            original['updatedAt'] = millis(node.updated_at)
            node.payload = {**node.payload, 'androidDocument': original}
            node.payload = {**node.payload, 'androidDocument': node_document(node)}
    return node


def check_version(node, value):
    # 所有编辑入口均显式提交版本，缺少版本也不得静默覆盖。
    expected = value.get('version')
    if type(expected) is not int or expected != node.version:
        raise APIError('人物资料已在其他页面更新，输入仍保留在草稿中。', 409, 'version_conflict')
    changed = db.session.execute(db.update(LifeNode).where(LifeNode.id == node.id, LifeNode.version == expected).values(version=expected + 1).execution_options(synchronize_session=False))
    if changed.rowcount != 1:
        raise APIError('人物资料已更新，请重新打开。', 409, 'version_conflict')


@bp.get('/graph')
@local_required
def graph():
    result = {kind: [] for kind in KINDS}
    for node in db.session.scalars(select(LifeNode).where(LifeNode.user_id == g.owner.id, LifeNode.is_deleted.is_(False)).order_by(LifeNode.created_at.desc())):
        result[node.kind].append(node_data(node))
    return {'data': result}


@bp.post('/graph/<kind>')
@local_required
def create(kind):
    value = body()
    if kind != 'entities' or value.get('type', 'person') != 'person':
        raise APIError('当前只开放人物资料。', 404)
    node = save_node(kind, value)
    db.session.commit()
    return {'data': node_data(node)}, 201


@bp.put('/graph/<kind>/<source_id>')
@local_required
def update(kind, source_id):
    if kind != 'entities':
        raise APIError('当前只开放人物资料。', 404)
    node = owned_node(kind, source_id)
    value = body()
    check_version(node, value)
    save_node(kind, value, node)
    db.session.commit()
    return {'data': node_data(node)}


@bp.delete('/graph/<kind>/<source_id>')
@local_required
def remove(kind, source_id):
    if kind != 'entities':
        raise APIError('当前只开放人物资料。', 404)
    node = owned_node(kind, source_id)
    check_version(node, body())
    for link in list(node.links):
        record = link.record
        changed = db.session.execute(db.update(LifeRecord).where(LifeRecord.id == record.id, LifeRecord.version == record.version).values(version=record.version + 1).execution_options(synchronize_session=False))
        if changed.rowcount != 1:
            raise APIError('关联记录已更新，未删除人物。', 409, 'version_conflict')
        record.version += 1
        record.updated_at = now()
        record.links.remove(link)
        db.session.flush()
        payload = dict(record.payload)
        if payload.get('androidDocument'):
            payload['androidDocument'] = {**payload['androidDocument'], 'updatedAt': millis(record.updated_at)}
            record.payload = payload
            record.payload = {**payload, 'androidDocument': record_document(record)}
    # 人物草稿中的预选关联同步解除，正式记录和原图始终保留。
    for draft in db.session.scalars(select(Draft).where(Draft.owner_id == g.owner.id, Draft.committed_at.is_(None), Draft.kind == 'record')):
        field = KINDS[kind]
        if source_id in draft.payload.get(field, []):
            draft.payload = {**draft.payload, field: [x for x in draft.payload[field] if x != source_id]}
            draft.version += 1
    node.is_deleted = True
    node.version += 1
    node.updated_at = now()
    original = deepcopy(node.payload.get('androidDocument')) or node_document(node)
    original['deletedAt'] = millis(node.updated_at)
    original['updatedAt'] = millis(node.updated_at)
    node.payload = {**node.payload, 'androidDocument': original}
    db.session.commit()
    return {'data': {'deleted': True, 'recordsRetained': True}}
