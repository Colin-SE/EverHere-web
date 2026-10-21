"""本机独立草稿：乐观锁、稳定事实 ID、保存回执与正式提交同一事务。"""
from copy import deepcopy
from uuid import uuid4

from flask import Blueprint, g
from sqlalchemy import select

from ..extensions import db
from ..models import Draft, LifeNode, LifeRecord, now
from ..security import APIError, body, local_required
from ..services.records import node_data, owned_record, record_data, save_record, validate_photos

bp = Blueprint('drafts', __name__, url_prefix='/api/v1/drafts')


def owned(draft_id):
    draft = db.session.get(Draft, draft_id)
    if not draft or draft.owner_id != g.owner.id:
        raise APIError('草稿不存在。', 404)
    return draft


def serialize(draft):
    return {'id': draft.id, 'kind': draft.kind, 'targetId': draft.target_id, 'baseVersion': draft.base_version,
            'version': draft.version, 'values': draft.payload, 'updatedAt': draft.updated_at.isoformat() + 'Z'}


def raw_values(value, previous=None):
    if not isinstance(value, dict):
        raise APIError('草稿内容须为 JSON 对象。')
    allowed = {'title', 'content', 'recordState', 'completionState', 'datePrecision', 'eventDate', 'eventStartAt', 'eventEndAt',
               'timezone', 'placeName', 'latitude', 'longitude', 'placePrecision', 'tags', 'mood', 'photoUris',
               'linkedEntityIds', 'linkedThreadIds', 'linkedChapterIds', 'showInTimeline', 'showOnGlobe',
               'name', 'summary', 'type', 'status', 'startDate', 'endDate'}
    result = deepcopy({k: v for k, v in value.items() if k in allowed})
    import json
    if len(json.dumps(result, ensure_ascii=True).encode()) > 4 * 1024 * 1024:
        raise APIError('草稿内容过大。', 413)
    if value.get('isPrivate') not in (None, False) or value.get('privacy', 'standard') != 'standard':
        raise APIError('旧保险箱功能已删除。')
    # 非法日期/坐标可以存草稿；照片授权必须现在验证，不能引用别的空间。
    photos = result.get('photoUris', [])
    if not isinstance(photos, list) or len(photos) > 10 or any(not isinstance(uri, str) for uri in photos):
        raise APIError('每条草稿最多 10 张照片。')
    validate_photos(photos, False, (previous or {}).get('photoUris', []))
    return result


@bp.get('')
@local_required
def listing():
    values = []
    for draft in db.session.scalars(select(Draft).where(Draft.owner_id == g.owner.id, Draft.committed_at.is_(None)).order_by(Draft.updated_at.desc(), Draft.id)):
        values.append(serialize(draft))
    return {'data': {'drafts': values}}


@bp.post('')
@local_required
def create():
    data = body()
    kind = data.get('kind', 'record')
    if kind not in ('record', 'person'):
        raise APIError('草稿类型无效。')
    target = data.get('recordId') if kind == 'record' else data.get('personId')
    previous, version = {}, 0
    if target:
        if kind == 'record':
            record = owned_record(target)
            previous, version = record_data(record), record.version
        else:
            from .graph import owned_node
            node = owned_node('entities', target)
            previous, version = node_data(node), node.version
        existing = db.session.scalar(select(Draft).where(Draft.owner_id == g.owner.id, Draft.kind == kind, Draft.target_id == target, Draft.committed_at.is_(None)).order_by(Draft.updated_at.desc()))
        if existing:
            return {'data': serialize(existing)}
    else:
        target = str(uuid4())
    values = {**previous, **data.get('values', {})} if isinstance(data.get('values', {}), dict) else None
    if values is None:
        raise APIError('初始草稿内容无效。')
    if data.get('personId') and kind == 'record':
        from .graph import owned_node
        person = owned_node('entities', data['personId'])
        values['linkedEntityIds'] = [person.source_id]
    draft = Draft(owner_id=g.owner.id, kind=kind, target_id=target, base_version=version, payload=raw_values(values, previous))
    db.session.add(draft)
    db.session.commit()
    return {'data': serialize(draft)}, 201


@bp.get('/<draft_id>')
@local_required
def detail(draft_id):
    draft = owned(draft_id)
    return {'data': serialize(draft)}


def compare(draft, value):
    if draft.committed_at:
        raise APIError('草稿已提交，请重新打开正式资料。', 409, 'draft_committed')
    expected = value.get('version')
    if type(expected) is not int or expected != draft.version:
        raise APIError('草稿已在另一页面更新；当前输入未覆盖，请保留后重新打开。', 409, 'draft_conflict')
    changed = db.session.execute(db.update(Draft).where(Draft.id == draft.id, Draft.version == expected, Draft.committed_at.is_(None)).values(version=expected + 1).execution_options(synchronize_session=False))
    if changed.rowcount != 1:
        raise APIError('草稿已变化，请重新打开。', 409, 'draft_conflict')
    draft.version += 1


@bp.put('/<draft_id>')
@local_required
def update(draft_id):
    draft, data = owned(draft_id), body()
    compare(draft, data)
    draft.payload = raw_values(data.get('values'), draft.payload)
    draft.updated_at = now()
    db.session.commit()
    return {'data': serialize(draft)}


@bp.delete('/<draft_id>')
@local_required
def discard(draft_id):
    draft, data = owned(draft_id), body()
    compare(draft, data)
    db.session.delete(draft)
    db.session.commit()
    return {'data': {'discarded': True}}


@bp.post('/<draft_id>/commit')
@local_required
def commit(draft_id):
    draft, data = owned(draft_id), body()
    # 回执优先于草稿版本检查，响应丢失的重试不会再次创建事实或复活已删资料。
    if draft.committed_at:
        return {'data': {'id': draft.target_id, 'kind': draft.kind, 'replayed': True}}
    compare(draft, data)
    values = deepcopy(draft.payload)
    if draft.kind == 'record':
        for key in ('latitude', 'longitude'):
            raw = values.get(key)
            if raw in ('', None):
                values[key] = None
            elif isinstance(raw, str):
                try:
                    values[key] = float(raw)
                except ValueError:
                    raise APIError('坐标格式无效；原始输入仍保留在草稿中。') from None
    if draft.kind == 'record':
        record = db.session.scalar(select(LifeRecord).where(LifeRecord.user_id == g.owner.id, LifeRecord.source_id == draft.target_id))
        if (record.version if record else 0) != draft.base_version or (record and record.is_deleted):
            raise APIError('正式记录已变化或已删除，草稿输入仍然保留。', 409, 'version_conflict')
        if record:
            changed = db.session.execute(db.update(LifeRecord).where(LifeRecord.id == record.id, LifeRecord.version == draft.base_version).values(version=draft.base_version + 1).execution_options(synchronize_session=False))
            if changed.rowcount != 1:
                raise APIError('正式记录已更新，草稿未覆盖。', 409, 'version_conflict')
        record = save_record({**values, 'actualDateConfirmed': data.get('actualDateConfirmed')}, record, source_id=draft.target_id)
    else:
        from .graph import check_version, save_node
        node = db.session.scalar(select(LifeNode).where(LifeNode.user_id == g.owner.id, LifeNode.kind == 'entities', LifeNode.source_id == draft.target_id))
        if (node.version if node else 0) != draft.base_version or (node and node.is_deleted):
            raise APIError('人物已变化或删除，人物草稿仍保留。', 409, 'version_conflict')
        if node:
            check_version(node, {'version': draft.base_version})
        save_node('entities', {**values, 'type': 'person'}, node, draft.target_id)
    draft.committed_at = now()
    draft.payload = {}
    db.session.commit()
    return {'data': {'id': draft.target_id, 'kind': draft.kind, 'replayed': False}}
