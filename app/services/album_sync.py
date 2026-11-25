"""Apply Android album operations to the records and photos used by Web."""
import hashlib
import json
from datetime import date
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import current_app, g
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import and_, func, or_, select

from ..extensions import db
from ..models import LifeNode, LifeRecord, Photo, RecordNode, now
from ..models_sync import AlbumAsset, AlbumChange, AlbumConflict, AlbumReceipt
from ..security import APIError
from .identity import fail, uuid
from .record_documents import millis, node_document, photo_metadata, record_document
from .record_schema import document, exact, int64, text
from .records import identifier


NODE_KINDS = {'entity': 'entities', 'thread': 'threads', 'chapter': 'chapters'}
MAX_VERSION = 2147483647


def operation(raw):
    value = exact(raw, ['operationId', 'installationId', 'localRevision', 'baseVersion', 'document'])
    uuid(value['installationId'])
    if not text(value['operationId'], maximum=256).strip():
        fail('invalid_id')
    int64(value['localRevision'], 1)
    int64(value['baseVersion'], 0)
    value['document'] = document(value['document'])
    return value


def subject(doc):
    identifier(doc['id'])
    model = LifeRecord if doc['type'] == 'record' else LifeNode
    conditions = [model.user_id == g.owner.id, model.source_id == doc['id']]
    if model == LifeNode:
        conditions.append(model.kind == NODE_KINDS[doc['type']])
    row = db.session.scalar(select(model).where(*conditions))
    if row and row.source_id != doc['id']:
        fail('id_collision', 409)
    return row


def append_change(kind, row, doc):
    change = AlbumChange(space_id=g.owner.id, kind=kind, subject_id=row.source_id, version=row.version, document=doc)
    db.session.add(change)
    db.session.flush()
    return change


def capture_web_changes():
    # Web writes and mobile writes hold the same LocalSpace row lock. Version equality
    # captures draft commits and relationship changes without relying on time precision.
    for kind, model in [('thread', LifeNode), ('chapter', LifeNode), ('entity', LifeNode), ('record', LifeRecord)]:
        published = select(AlbumChange.sequence).where(
            AlbumChange.space_id == model.user_id, AlbumChange.kind == kind,
            AlbumChange.subject_id == model.source_id, AlbumChange.version == model.version,
        ).exists()
        statement = select(model).where(model.user_id == g.owner.id, ~published)
        if model == LifeNode:
            statement = statement.where(model.kind == NODE_KINDS[kind])
        else:
            statement = statement.where(model.privacy == 'standard')
        for row in db.session.scalars(statement.order_by(model.id)):
            if model == LifeRecord:
                doc = record_document(row)
                if row.is_deleted and doc['deletedAt'] is None:
                    doc['deletedAt'] = millis(row.updated_at)
            else:
                doc = node_document(row)
                if row.is_deleted and doc['deletedAt'] is None:
                    doc['deletedAt'] = millis(row.updated_at)
            append_change(kind, row, doc)


def saved_document(row, kind):
    if row is None:
        return None
    change = db.session.scalar(select(AlbumChange).where(
        AlbumChange.space_id == g.owner.id, AlbumChange.kind == kind,
        AlbumChange.subject_id == row.source_id, AlbumChange.version == row.version,
    ))
    if change is None:
        capture_web_changes()
        change = db.session.scalar(select(AlbumChange).where(
            AlbumChange.space_id == g.owner.id, AlbumChange.kind == kind,
            AlbumChange.subject_id == row.source_id, AlbumChange.version == row.version,
        ))
    if change is None:
        fail('unsupported_privacy', 409)
    return {'serverVersion': str(change.version), 'document': change.document}


def photo_row(asset_id):
    identifier(asset_id)
    rows = db.session.scalars(select(Photo).where(Photo.user_id == g.owner.id, or_(
        Photo.source_id == asset_id, and_(Photo.source_id.is_(None), Photo.id == asset_id),
    )))
    return next((p for p in rows if (p.source_id or p.id) == asset_id), None)


def asset_metadata(photo):
    asset = db.session.get(AlbumAsset, photo.id)
    return asset, asset.spec if asset else photo_metadata(photo)


def record_assets(specs):
    uris = []
    for spec in specs:
        photo = photo_row(spec['id'])
        if photo is None:
            if len(spec['mimeType']) > 30:
                fail('invalid_photo')
            photo = Photo(user_id=g.owner.id, source_id=spec['id'], content_type=spec['mimeType'], data=b'')
            db.session.add(photo)
            db.session.flush()
            db.session.add(AlbumAsset(photo_id=photo.id, spec=spec))
        elif asset_metadata(photo)[1] != spec:
            fail('asset_metadata_conflict', 409)
        uris.append(f'/api/v1/photos/{photo.id}')
    return uris


def links(kind, ids, deleted):
    if not ids:
        return []
    for value in ids:
        identifier(value)
    statement = select(LifeNode).where(
        LifeNode.user_id == g.owner.id, LifeNode.kind == NODE_KINDS[kind], LifeNode.source_id.in_(ids),
    )
    if not deleted:
        statement = statement.where(LifeNode.is_deleted.is_(False))
    rows = {row.source_id: row for row in db.session.scalars(statement)}
    if set(rows) != set(ids):
        fail('missing_relation', 409)
    return [rows[value] for value in ids]


def record_fields(row, doc):
    if len(doc['title']) > 200 or len(doc['timezone']) > 256:
        fail('unsupported_web_field', 422)
    try:
        ZoneInfo(doc['timezone'])
    except (ValueError, ZoneInfoNotFoundError):
        fail('invalid_timezone')
    area_before = row.payload.get('androidDocument', {}).get('administrativeArea') if row.payload else None
    if area_before and 'administrativeArea' not in doc:
        fail('location_client_upgrade_required', 409)
    point = doc['coordinates'] or {}
    event = doc['eventDate']
    row.title, row.content = doc['title'], doc['content']
    row.record_state, row.privacy = doc['recordState'], 'standard'
    row.event_date = None
    if event['precision'] in ('day', 'range'):
        try:
            candidate = date.fromisoformat(event['start'])
            if candidate.year >= 1000 or db.engine.dialect.name != 'mysql':
                row.event_date = candidate
        except ValueError:
            pass  # The full date is preserved in the document even outside SQL DATE range.
    related = [node for kind in NODE_KINDS for node in links(kind, doc[kind + 'Ids'], row.is_deleted)]
    row.payload = {**(row.payload or {}), **{key: doc[key] for key in (
        'completionState', 'timezone', 'placeName', 'tags', 'mood', 'showInTimeline', 'showOnGlobe',
    )}, 'eventDate': event['start'], 'eventStartAt': event['start'], 'eventEndAt': event['end'],
        'datePrecision': event['precision'], 'latitude': point.get('latitude'), 'longitude': point.get('longitude'),
        'placePrecision': point.get('precision'), 'photoUris': record_assets(doc['photos']), 'source': 'manual',
        'deletedAt': doc['deletedAt'], 'androidDocument': doc}
    row.links.clear()
    db.session.flush()
    row.links = [RecordNode(node_id=node.id) for node in related]


def write(doc, row):
    kind = doc['type']
    deleted = doc['deletedAt'] is not None
    if row is not None and row.version >= MAX_VERSION:
        fail('version_exhausted', 409)
    if kind == 'record':
        if row is not None and row.privacy != 'standard':
            fail('unsupported_privacy', 409)
        if row is None:
            row = LifeRecord(user_id=g.owner.id, source_id=doc['id'], version=0)
    else:
        if row is None:
            row = LifeNode(user_id=g.owner.id, source_id=doc['id'], kind=NODE_KINDS[kind], version=0)
        row.name = doc['name'] if kind == 'entity' else doc['title']
        if len(row.name) > 120:
            fail('unsupported_web_field', 422)
    row.version += 1
    row.is_deleted, row.updated_at = deleted, now()
    db.session.add(row)
    if kind == 'record':
        # The initial fields are required before queries flush a new record.
        row.title, row.content, row.record_state = doc['title'], doc['content'], doc['recordState']
        record_fields(row, doc)
    else:
        prior = row.payload or {}
        row.payload = {**prior, 'name': row.name, 'androidDocument': doc}
        if kind == 'entity':
            row.payload.update(type=doc['kind'], summary=doc['meaning'])
        if kind == 'chapter':
            links('thread', doc['threadIds'], deleted)
            if deleted:
                doc = {**doc, 'threadIds': []}
                row.payload = {**row.payload, 'androidDocument': doc}
        if deleted:
            from ..api.graph import unlink_node
            unlink_node(row)
            if kind == 'thread':
                unlink_chapters(row.source_id)
    return append_change(kind, row, doc)


def unlink_chapters(thread_id):
    for chapter in db.session.scalars(select(LifeNode).where(LifeNode.user_id == g.owner.id, LifeNode.kind == 'chapters')):
        source = chapter.payload.get('androidDocument')
        if not source or thread_id not in source['threadIds']:
            continue
        chapter.version += 1
        chapter.updated_at = now()
        revised = {**source, 'updatedAt': millis(chapter.updated_at), 'threadIds': [value for value in source['threadIds'] if value != thread_id]}
        chapter.payload = {**chapter.payload, 'androidDocument': revised}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode()).hexdigest()


def receipt(op, request_hash):
    key = digest(op['operationId'])
    row = db.session.get(AlbumReceipt, (g.owner.id, key))
    if row and row.request_hash != request_hash:
        fail('operation_reused', 409)
    return key, row.response if row else None


def save_receipt(key, request_hash, response):
    db.session.add(AlbumReceipt(space_id=g.owner.id, operation_hash=key, request_hash=request_hash, response=response))
    return response


def applied(change):
    return {'sequence': str(change.sequence), 'serverVersion': str(change.version), 'document': change.document}


def push(op):
    doc = op['document']
    request_hash = digest(['push', op])
    key, prior = receipt(op, request_hash)
    if prior is not None:
        return prior
    row = subject(doc)
    result = {name: op[name] for name in ('operationId', 'localRevision')}
    if int(op['baseVersion']) != (row.version if row else 0):
        remote = saved_document(row, doc['type'])
        if not remote:
            fail('missing_base', 409)
        conflict = AlbumConflict(space_id=g.owner.id, operation_id=op['operationId'], base_version=int(op['baseVersion']),
                                 remote_version=row.version, local_document=doc, remote_document=remote['document'])
        db.session.add(conflict)
        db.session.flush()
        result.update(status='conflict', conflictId=conflict.id, remote=remote)
    else:
        capture_web_changes()
        result.update(status='applied', **applied(write(doc, row)))
    return save_receipt(key, request_hash, result)


def sequence():
    return db.session.scalar(select(func.max(AlbumChange.sequence)).where(AlbumChange.space_id == g.owner.id)) or 0


def page_size(value):
    if type(value) is not int or not 1 <= value <= 4:
        fail('invalid_page_size')
    return value


def pull(installation, cursor, limit):
    serializer = URLSafeTimedSerializer(current_app.config['IDENTITY_SECRET'], salt='album-sync-cursor-v1')
    binding = [g.owner.id, installation]
    after = 0
    if cursor is not None:
        if not isinstance(cursor, str) or len(cursor) > 4096:
            fail('invalid_cursor')
        try:
            bound_space, bound_installation, after = serializer.loads(cursor, max_age=30 * 86400)
        except SignatureExpired:
            fail('cursor_expired', 409)
        except (BadSignature, ValueError, TypeError):
            fail('invalid_cursor')
        if [bound_space, bound_installation] != binding or type(after) is not int or after < 0:
            fail('invalid_cursor')
    capture_web_changes()
    watermark = sequence()
    rows = list(db.session.scalars(select(AlbumChange).where(
        AlbumChange.space_id == g.owner.id, AlbumChange.sequence > after,
    ).order_by(AlbumChange.sequence).limit(limit + 1)))
    items = [applied(row) for row in rows[:limit]]
    position = int(items[-1]['sequence']) if items else after
    return {'mode': 'changes', 'items': items, 'hasMore': len(rows) > limit, 'watermark': str(watermark),
            'cursor': serializer.dumps([*binding, position])}


def conflicts(after, limit):
    statement = select(AlbumConflict).where(AlbumConflict.space_id == g.owner.id, AlbumConflict.resolved.is_(False))
    if after is not None:
        statement = statement.where(AlbumConflict.id > uuid(after))
    rows = list(db.session.scalars(statement.order_by(AlbumConflict.id).limit(limit + 1)))
    more = len(rows) > limit
    return {'conflicts': [{'conflictId': row.id, 'operationId': row.operation_id, 'baseVersion': str(row.base_version),
                           'remoteVersion': str(row.remote_version), 'local': row.local_document, 'remote': row.remote_document}
                          for row in rows[:limit]], 'hasMore': more, 'afterId': rows[limit - 1].id if more else None}


def resolve(value, op):
    conflict_id, choice = uuid(value['conflictId']), value['choice']
    expected = int(int64(value['expectedRemoteVersion'], 1))
    if choice not in ('local', 'remote', 'both', 'manual'):
        fail('invalid_resolution')
    req_hash = digest(['resolve', conflict_id, choice, expected, op])
    key, prior = receipt(op, req_hash)
    if prior is not None:
        return prior
    conflict = db.session.get(AlbumConflict, conflict_id)
    if not conflict or conflict.space_id != g.owner.id:
        fail('conflict_not_found', 404)
    if conflict.resolved:
        fail('conflict_already_resolved', 409)
    local, doc = conflict.local_document, op['document']
    row = subject(local)
    if not row or row.version != expected:
        fail('stale_conflict', 409)
    remote = saved_document(row, local['type'])
    copying = choice == 'both'
    if (doc['type'] != local['type'] or (doc['id'] == local['id']) == copying
            or int(op['baseVersion']) != (0 if copying else expected)):
        fail('invalid_resolution')
    if choice in ('local', 'both') and doc != {**local, 'id': doc['id']}:
        fail('invalid_resolution')
    if choice == 'remote' and doc != remote['document']:
        fail('invalid_resolution')
    if copying and subject(doc):
        fail('copy_id_exists', 409)
    capture_web_changes()
    result = {'sequence': str(sequence()), **remote} if choice == 'remote' else applied(write(doc, None if copying else row))
    conflict.resolved = True
    return save_receipt(key, req_hash, {**result, 'status': 'resolved', 'conflictId': conflict_id, 'choice': choice,
                                        'operationId': op['operationId'], 'localRevision': op['localRevision']})
