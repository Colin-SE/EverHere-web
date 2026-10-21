"""普通 ZIP 与本机恢复暂存：固定条目、原字节校验、显式确认和幂等回执。"""
import base64
import hashlib
import json
from datetime import timedelta
from io import BytesIO
from pathlib import Path
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app, g
from PIL import Image
from sqlalchemy import select

from ..extensions import db
from ..models import ArchiveJob, Photo, now
from ..security import APIError
from .android_archive import export_android
from .archive import apply_data, local_fingerprint, plan
from sync_contract import android_json, parse_archive

MAX_ARCHIVE = 128 * 1024 * 1024


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('重复 JSON 字段')
            result[key] = value
        return result
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        def walk(item, depth=0):
            if depth > 32:
                raise ValueError()
            if isinstance(item, dict):
                for child in item.values():
                    walk(child, depth+1)
            elif isinstance(item, list):
                if len(item) > 100000:
                    raise ValueError()
                for child in item:
                    walk(child, depth+1)
        walk(value)
        return value
    except (ValueError, UnicodeError, RecursionError):
        raise APIError('归档不是有效的有界 UTF-8 JSON，或存在重复字段。') from None


def decode(raw):
    if len(raw) > MAX_ARCHIVE:
        raise APIError('Web 单次归档上限为 128 MB，请使用较小的普通资料包。', 413)
    region = current_app.config.get('CLOUD_REGION', 'cn')
    originals = {}
    if raw.startswith(b'PK'):
        try:
            with ZipFile(BytesIO(raw)) as archive:
                names = archive.namelist()
                if len(names) > 10003 or len(names) != len(set(names)) or names[:2] != ['manifest.json', 'data.json']:
                    raise ValueError()
                for item in archive.infolist():
                    name = item.filename
                    if item.is_dir() or name.startswith('/') or '\\' in name or ':' in name or any(x in ('', '.', '..') for x in name.split('/')):
                        raise ValueError()
                    cap = 1024*1024 if name == 'manifest.json' else 16*1024*1024 if name == 'data.json' else 50*1024*1024
                    if item.file_size > cap:
                        raise ValueError()
                if sum(item.file_size for item in archive.infolist()) > MAX_ARCHIVE:
                    raise ValueError()
                info = strict_json(archive.read('manifest.json'))
                data_bytes = archive.read('data.json')
                data = strict_json(data_bytes)
                value = {'format': 'everhere-archive', 'archiveVersion': 1, 'manifest': info, 'data': data}
                parsed = parse_archive(value, region, kind='zip', data_bytes=data_bytes)
                expected = {'manifest.json', 'data.json', *(asset['entry'] for asset in info['assets'])}
                if set(names) != expected:
                    raise ValueError()
                for asset in info['assets']:
                    content = archive.read(asset['entry'])
                    if len(content) != int(asset['byteSize']) or hashlib.sha256(content).hexdigest() != asset['sha256']:
                        raise ValueError()
                    with Image.open(BytesIO(content)) as image:
                        if image.width * image.height > 100000000 or Image.MIME.get(image.format) != asset['mimeType'] or image.size != (asset['width'], asset['height']):
                            raise ValueError()
                        image.verify()
                    originals[asset['id']] = {'metadata': {key: asset[key] for key in ('id','mimeType','sha256','byteSize','width','height')}, 'bytes': content}
                return value, parsed, originals
        except (BadZipFile, KeyError, TypeError, ValueError, OSError, RuntimeError, Image.DecompressionBombError):
            raise APIError('ZIP 条目、长度、原图或摘要校验失败，未写入任何正式资料。') from None
    if len(raw) > 16*1024*1024:
        raise APIError('普通 JSON 不能超过 16 MB。', 413)
    value = strict_json(raw)
    return value, parse_archive(value, region), originals


def stage_path(job):
    root = Path(current_app.config.get('ARCHIVE_STAGE_DIRECTORY') or (Path(current_app.instance_path) / 'archive-stage')).resolve()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    target = (root / (job.id + '.bin')).resolve()
    if not target.is_relative_to(root):
        raise APIError('本机归档路径无效。', 500)
    return target


def cipher(job):
    secret = str(current_app.config['SECRET_KEY']) + ':archive-stage-v1:' + job.owner_id
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest()))


def get_job(identifier):
    job = db.session.get(ArchiveJob, identifier)
    if not job or job.owner_id != g.owner.id:
        raise APIError('本机归档预览不存在。', 404)
    return job


def describe(job):
    return {'id': job.id, **job.summary, 'createdAt': job.created_at.isoformat()+'Z', 'completed': bool(job.committed_at)}


def preview_file(raw):
    value, data, originals = decode(raw)
    _, summary, _ = plan(data)
    summary.update(kind=value['manifest']['kind'], missingOriginals=value['manifest']['missingOriginals'], externalPhotos=len(value['manifest']['missingOriginals']))
    job = ArchiveJob(owner_id=g.owner.id, source_hash=hashlib.sha256(raw).hexdigest(), target_hash=local_fingerprint(), summary=summary)
    db.session.add(job)
    db.session.flush()
    path = stage_path(job)
    try:
        with path.open('xb') as file:
            file.write(cipher(job).encrypt(raw))
        db.session.commit()
    except Exception:
        db.session.rollback()
        path.unlink(missing_ok=True)
        raise
    return describe(job)


def read_job(job):
    if job.created_at < now()-timedelta(days=1):
        raise APIError('预览已超过 24 小时，请重新选择原始文件。', 409, 'preview_expired')
    try:
        raw = cipher(job).decrypt(stage_path(job).read_bytes())
    except (OSError, InvalidToken):
        raise APIError('本机暂存不可读取，请保留原文件并重新选择。', 409, 'preview_unavailable') from None
    if hashlib.sha256(raw).hexdigest() != job.source_hash:
        raise APIError('本机暂存摘要不符，未执行恢复。', 409)
    return decode(raw)


def confirm_job(identifier, value):
    job = get_job(identifier)
    if job.committed_at:
        return {**describe(job), 'replayed': True}
    if value.get('confirmed') is not True:
        raise APIError('请明确确认本次恢复范围。')
    if job.target_hash != local_fingerprint():
        raise APIError('本机记录、草稿或人物已变化，请重新预览，当前资料未被覆盖。', 409, 'import_changed')
    archive, data, originals = read_job(job)
    if archive['manifest']['missingOriginals'] and value.get('acceptMissingPhotos') is not True:
        raise APIError('JSON 不包含原图，请单独确认接受缺图恢复。')
    result = apply_data(data, value.get('copyConflicts') is True, originals)
    job.committed_at = now()
    job.summary = {**result, 'kind': archive['manifest']['kind'], 'missingOriginals': archive['manifest']['missingOriginals']}
    db.session.commit()
    # 正式资料提交后只清本次加密暂存；清理失败不把已提交的事务冒充失败。
    try:
        stage_path(job).unlink(missing_ok=True)
    except OSError:
        return {**describe(job), 'cleanupPending': True}
    return describe(job)


def export_zip():
    value = export_android()
    data_bytes = android_json(value['data'])
    info = value['manifest']
    info.update(kind='zip', complete=True, missingOriginals=[], dataBytes=str(len(data_bytes)), dataSha256=hashlib.sha256(data_bytes).hexdigest())
    contents = []
    total = len(data_bytes)
    for asset in info['assets']:
        photo = db.session.scalar(select(Photo).where(Photo.user_id == g.owner.id, Photo.source_id == asset['id']))
        if not photo:
            by_id = db.session.get(Photo, asset['id'])
            photo = by_id if by_id and by_id.user_id == g.owner.id else None
        if not photo or hashlib.sha256(photo.data).hexdigest() != asset['sha256']:
            raise APIError('本机原图尚未完整恢复，不能生成完整 ZIP；可导出明确无原图的 JSON。', 409, 'original_missing')
        total += len(photo.data)
        if total > MAX_ARCHIVE:
            raise APIError('Web 单次 ZIP 上限为 128 MB，未生成不完整备份。', 413)
        asset['entry'] = 'originals/' + hashlib.sha256(asset['id'].encode()).hexdigest() + '.bin'
        contents.append((asset['entry'], photo.data))
    output = BytesIO()
    with ZipFile(output, 'w', compression=ZIP_DEFLATED) as archive:
        archive.writestr('manifest.json', android_json(info))
        archive.writestr('data.json', data_bytes)
        for entry, content in contents:
            archive.writestr(entry, content)
    raw = output.getvalue()
    if len(raw) > MAX_ARCHIVE:
        raise APIError('ZIP 超出 Web 单次大小上限。', 413)
    # 自检实际输出，只有可重新校验的原图包才交给下载请求。
    decode(raw)
    return raw
