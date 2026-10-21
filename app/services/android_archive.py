"""普通归档的共同有类型文档，原始审计与照片顺序始终保留。"""
import hashlib
from datetime import datetime, timezone
from io import BytesIO

from flask import current_app, g
from PIL import Image
from sqlalchemy import select

from ..extensions import db
from ..models import LifeNode, LifeRecord, Photo, Reminder
from ..security import APIError
from .records import record_data
from .record_query import record_date
from sync_contract import android_json, document


def millis(value):
    epoch = datetime(1970, 1, 1)
    delta = value.replace(tzinfo=None) - epoch
    return str(delta.days * 86400000 + delta.seconds * 1000 + delta.microseconds // 1000)


def photo_metadata(photo):
    with Image.open(BytesIO(photo.data)) as image:
        width, height = image.size
    return {'id': photo.source_id or photo.id, 'mimeType': photo.content_type,
            'sha256': hashlib.sha256(photo.data).hexdigest(), 'byteSize': str(len(photo.data)), 'width': width, 'height': height}


def record_document(record):
    value = record_data(record)
    original = value.get('androidDocument', {})
    originals = {p['id']: p for p in original.get('photos', [])}
    photos = []
    for uri in value.get('photoUris', []):
        if uri.startswith('asset:') and uri[6:] in originals:
            photos.append(originals[uri[6:]])
            continue
        if not uri.startswith('/api/v1/photos/'):
            raise APIError('照片没有可信原图元数据，请先重新选择照片或保留旧格式备份。')
        photo = db.session.get(Photo, uri.rsplit('/', 1)[-1])
        if not photo or photo.user_id != g.owner.id:
            raise APIError('照片不可读取。')
        photos.append(photo_metadata(photo))
    point = None if value.get('latitude') is None else {'latitude': value['latitude'], 'longitude': value['longitude'], 'precision': value.get('placePrecision') or 'city'}
    common = {'type': 'record', 'id': record.source_id, 'createdAt': original.get('createdAt', millis(record.created_at)),
              'updatedAt': original.get('updatedAt', millis(record.updated_at)), 'deletedAt': value.get('deletedAt', original.get('deletedAt')) if record.is_deleted else None,
              'title': record.title, 'content': record.content, 'recordState': record.record_state, 'completionState': value['completionState'],
              'eventDate': record_date(value), 'timezone': value.get('timezone', original.get('timezone', current_app.config.get('EVENT_TIMEZONE', 'Asia/Shanghai'))),
              'placeName': value.get('placeName') or None, 'coordinates': point, 'tags': value.get('tags', []), 'mood': value.get('mood') or None,
              'showInTimeline': value.get('showInTimeline', True), 'showOnGlobe': value.get('showOnGlobe', False), 'privacy': 'standard',
              'entityIds': value.get('linkedEntityIds', []), 'threadIds': value.get('linkedThreadIds', []), 'chapterIds': value.get('linkedChapterIds', []), 'photos': photos}
    return document(common)


def node_document(node):
    original = node.payload.get('androidDocument', {})
    subject = {'entities': 'entity', 'threads': 'thread', 'chapters': 'chapter'}[node.kind]
    common = {'type': subject, 'id': node.source_id, 'createdAt': original.get('createdAt', millis(node.created_at)),
              'updatedAt': original.get('updatedAt', millis(node.updated_at)), 'deletedAt': original.get('deletedAt') if node.is_deleted else None}
    if subject == 'entity':
        common.update(kind=node.payload.get('type', 'person'), name=node.name, meaning=node.payload.get('summary', ''))
    else:
        if not original and (node.payload.get('summary') or node.payload.get('status', 'active') != 'active'):
            raise APIError('旧 Web 线索/阶段包含 Android 当前不支持的字段，请使用兼容备份。')
        common['title'] = node.name
        if subject == 'chapter':
            start, end = node.payload.get('startDate'), node.payload.get('endDate')
            common.update(eventDate=original.get('eventDate', {'precision': 'range' if start and end else 'day' if start else 'unknown', 'start': start, 'end': end}), threadIds=original.get('threadIds', []))
    return document(common)


def documents():
    result = []
    for kind in ('entities', 'threads', 'chapters'):
        result.extend(node_document(node) for node in db.session.scalars(select(LifeNode).where(LifeNode.user_id == g.owner.id, LifeNode.kind == kind).order_by(LifeNode.source_id)))
    result.extend(record_document(row) for row in db.session.scalars(select(LifeRecord).where(LifeRecord.user_id == g.owner.id).order_by(LifeRecord.source_id)))
    return result


def export_android():
    docs = documents()
    ordinary_ids={doc['id'] for doc in docs if doc['type']=='record'}
    reminders=[row.payload for row in db.session.scalars(select(Reminder).where(Reminder.owner_id==g.owner.id)) if row.payload.get('recordId') is None or row.payload['recordId'] in ordinary_ids]
    data = {'documents': docs, 'reminders': reminders}
    encoded = android_json(data)
    photos = {photo['id']: photo for doc in docs for photo in doc.get('photos', [])}
    info = {'format': 'everhere-archive', 'archiveVersion': 1, 'kind': 'json', 'region': current_app.config.get('CLOUD_REGION', 'cn'),
            'createdAt': millis(datetime.now(timezone.utc)), 'appVersion': 'web-local-2026.10', 'versionCode': 2, 'databaseVersion': 2,
            'dataSha256': hashlib.sha256(encoded).hexdigest(), 'dataBytes': str(len(encoded)),
            'counts': {**{kind: sum(d['type'] == kind for d in docs) for kind in ('record', 'entity', 'thread', 'chapter')}, 'reminder': len(reminders), 'photo': len(photos)},
            'assets': [{**photo, 'entry': None} for photo in photos.values()], 'missingOriginals': list(photos), 'protectedExcluded': True, 'complete': False}
    return {'format': 'everhere-archive', 'archiveVersion': 1, 'manifest': info, 'data': data}
