"""既有记录的元数据维护；仅供保存、软删除和人物解绑使用。"""
import hashlib
from datetime import datetime
from io import BytesIO

from flask import current_app, g
from PIL import Image

from ..extensions import db
from ..models import Photo
from ..security import APIError
from .records import record_data
from .record_query import record_date
from .record_schema import document


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
