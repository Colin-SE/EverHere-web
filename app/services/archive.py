"""仅保留当前安卓版普通归档；预览、确定性副本和事务恢复。"""
import hashlib
import json
from copy import deepcopy
from uuid import NAMESPACE_URL, uuid5

from flask import current_app, g
from sqlalchemy import select

from ..extensions import db
from ..models import Draft, LifeNode, LifeRecord, Photo, Reminder
from ..security import APIError
from .android_archive import node_document, photo_metadata, record_document
from .records import normalize_node, save_record
from sync_contract import native_projection, parse_archive


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def local_fingerprint():
    records = [(r.id, r.version, r.is_deleted) for r in db.session.scalars(select(LifeRecord).where(LifeRecord.user_id == g.owner.id))]
    nodes = [(n.id, n.version, n.is_deleted) for n in db.session.scalars(select(LifeNode).where(LifeNode.user_id == g.owner.id))]
    drafts = [(d.id, d.version, d.kind, d.target_id) for d in db.session.scalars(select(Draft).where(Draft.owner_id == g.owner.id, Draft.committed_at.is_(None)))]
    photos = [(p.id, p.source_id, len(p.data)) for p in db.session.scalars(select(Photo).where(Photo.user_id == g.owner.id))]
    reminders = [(r.id, r.payload) for r in db.session.scalars(select(Reminder).where(Reminder.owner_id == g.owner.id))]
    return fingerprint({'records': sorted(records), 'nodes': sorted(nodes), 'drafts': sorted(drafts), 'photos': sorted(photos), 'reminders': sorted(reminders)})


def existing_documents():
    known = {}
    for row in db.session.scalars(select(LifeNode).where(LifeNode.user_id == g.owner.id)):
        doc = node_document(row)
        known[doc['type'], doc['id']] = doc
    for row in db.session.scalars(select(LifeRecord).where(LifeRecord.user_id == g.owner.id)):
        doc = record_document(row)
        known['record', row.source_id] = doc
        for photo in doc.get('photos', []):
            known.setdefault(('photo', photo['id']), photo)
    for row in db.session.scalars(select(Reminder).where(Reminder.owner_id == g.owner.id)):
        known['reminder', row.source_id] = row.payload
    for row in db.session.scalars(select(Photo).where(Photo.user_id == g.owner.id)):
        known['photo', row.source_id or row.id] = photo_metadata(row)
    return known


def plan(data, copies=False):
    source = deepcopy(data)
    known = existing_documents()
    busy = {('record' if d.kind == 'record' else 'entity', d.target_id) for d in db.session.scalars(select(Draft).where(Draft.owner_id == g.owner.id, Draft.committed_at.is_(None)))}
    all_values = [(d['type'], d) for d in source['documents']] + [('reminder', r) for r in source['reminders']]
    photo_map = {p['id']: p for d in source['documents'] for p in d.get('photos', [])}
    all_values += [('photo', p) for p in photo_map.values()]
    problems = [{'kind': kind, 'id': value['id']} for kind, value in all_values if (kind, value['id']) in busy or ((kind, value['id']) in known and known[kind, value['id']] != value)]
    mapping = {}
    source_key = fingerprint(source)
    def alias(kind, old):
        mapping[kind, old] = str(uuid5(NAMESPACE_URL, f'everhere-archive:{g.owner.id}:{source_key}:{kind}:{old}'))
    if copies:
        for problem in problems:
            alias(problem['kind'], problem['id'])
        # 引用副本的既有记录也须复制，不能为更换关系覆盖原记录。
        changed = True
        while changed:
            changed = False
            for kind, value in all_values:
                references = [(related, identifier) for related in ('entity', 'thread', 'chapter') for identifier in value.get(related+'Ids', [])]
                references += [('photo', p['id']) for p in value.get('photos', [])]
                if value.get('recordId'):
                    references.append(('record', value['recordId']))
                key = kind, value['id']
                if key in known and key not in mapping and any(reference in mapping for reference in references):
                    alias(*key); changed = True
        for kind, value in all_values:
            old = value['id']; value['id'] = mapping.get((kind, old), old)
            for related in ('entity', 'thread', 'chapter'):
                if related+'Ids' in value:
                    value[related+'Ids'] = [mapping.get((related, identifier), identifier) for identifier in value[related+'Ids']]
            if value.get('recordId'):
                value['recordId'] = mapping.get(('record', value['recordId']), value['recordId'])
            for photo in value.get('photos', []):
                photo['id'] = mapping.get(('photo', photo['id']), photo['id'])
    summary = {'total': sum(d['type'] == 'record' for d in source['documents']), 'newRecords': 0, 'skippedRecords': 0,
               'conflicts': problems, 'entities': sum(d['type'] == 'entity' for d in source['documents']),
               'threads': sum(d['type'] == 'thread' for d in source['documents']), 'chapters': sum(d['type'] == 'chapter' for d in source['documents']),
               'reminders': len(source['reminders']), 'photoCount': len(photo_map), 'copies': len(mapping), 'android': True}
    for doc in source['documents']:
        if doc['type'] == 'record':
            if ('record', doc['id']) in known:
                summary['skippedRecords'] += 1
            else:
                summary['newRecords'] += 1
    return source, summary, mapping


def prepare(archive):
    data = parse_archive(archive, current_app.config.get('CLOUD_REGION', 'cn'))
    _, summary, _ = plan(data)
    return data, {**summary, 'fingerprint': fingerprint(archive), 'targetFingerprint': local_fingerprint(),
                  'missingOriginals': archive['manifest']['missingOriginals'], 'externalPhotos': len(archive['manifest']['missingOriginals'])}


def apply_data(data, copies=False, originals=None):
    transformed, summary, mapping = plan(data, copies)
    if summary['conflicts'] and not copies:
        raise APIError('存在同 ID 内容、删除状态或草稿冲突，请明确选择保留两份。', 409, 'import_conflict')
    if originals:
        for source_id, value in originals.items():
            target = mapping.get(('photo', source_id), source_id)
            existing = db.session.scalar(select(Photo).where(Photo.user_id == g.owner.id, Photo.source_id == target))
            if not existing:
                # 普通 Web 资产的稳定 ID 原本就是主键，也可直接复用。
                by_id = db.session.get(Photo, target)
                existing = by_id if by_id and by_id.user_id == g.owner.id else None
            if not existing:
                db.session.add(Photo(user_id=g.owner.id, source_id=target, content_type=value['metadata']['mimeType'], data=value['bytes']))
    db.session.flush()
    projected = native_projection(transformed)
    for kind in ('entities', 'threads', 'chapters'):
        for raw in projected['graph'][kind]:
            prior = db.session.scalar(select(LifeNode).where(LifeNode.user_id == g.owner.id, LifeNode.kind == kind, LifeNode.source_id == raw['id']))
            if not prior:
                value = normalize_node(kind, raw)
                db.session.add(LifeNode(user_id=g.owner.id, kind=kind, source_id=raw['id'], name=value['name'], payload=value, is_deleted=raw['androidDocument']['deletedAt'] is not None))
    db.session.flush()
    for raw in projected['records']:
        prior = db.session.scalar(select(LifeRecord).where(LifeRecord.user_id == g.owner.id, LifeRecord.source_id == raw['id']))
        if prior:
            continue
        # 有原图文件时转换为本机授权地址；原始 assetId 仍在照片元信息内。
        uris = []
        for uri in raw['photoUris']:
            asset = uri[6:]
            photo = db.session.scalar(select(Photo).where(Photo.user_id == g.owner.id, Photo.source_id == asset)) or db.session.get(Photo, asset)
            uris.append(f'/api/v1/photos/{photo.id}' if photo and photo.user_id == g.owner.id else uri)
        raw['photoUris'] = uris
        record = save_record(raw, importing=True, source_id=raw['id'])
        record.payload = {**record.payload, 'photoUris': uris}
    for value in transformed['reminders']:
        if not db.session.scalar(select(Reminder).where(Reminder.owner_id == g.owner.id, Reminder.source_id == value['id'])):
            db.session.add(Reminder(owner_id=g.owner.id, source_id=value['id'], payload=value))
    return summary


def merge(archive, expected_fingerprint, target_fingerprint=None, copies=False, accept_missing=False):
    data, preview = prepare(archive)
    if expected_fingerprint != preview['fingerprint'] or target_fingerprint != preview['targetFingerprint']:
        raise APIError('归档或本机资料已变化，请重新预览。', 409, 'import_changed')
    if preview['missingOriginals'] and accept_missing is not True:
        raise APIError('JSON 不含原图，请明确接受缺图恢复，或改用完整 ZIP。')
    result = apply_data(data, copies)
    db.session.commit()
    return result
