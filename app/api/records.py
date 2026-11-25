"""记录与照片接口，所有路径均校验所有者。"""

from io import BytesIO
from hashlib import sha256
from uuid import UUID
import warnings

from flask import Blueprint, g, request, send_file
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import func, select

from ..extensions import db
from ..models import LifeRecord, Photo, now
from ..security import APIError, body, local_required, page_number
from ..services.records import owned_record, record_data, save_record
from ..services.record_query import select_records

bp = Blueprint("records", __name__, url_prefix="/api/v1")


@bp.get("/records")
@local_required
def listing():
    if request.args.get('page') is not None:
        page = page_number()
        records, total = select_records(request.args, page=page)
        return {"data": {"records": records, "total": total, "page": page, "pageSize": 30}}
    records = select_records(request.args)
    return {"data": {"records": records, "total": len(records)}}


@bp.post("/records")
@local_required
def create():
    record = save_record(body())
    db.session.commit()
    return {"data": record_data(record)}, 201


@bp.get("/records/<source_id>")
@local_required
def detail(source_id):
    return {"data": record_data(owned_record(source_id))}


@bp.put("/records/<source_id>")
@local_required
def update(source_id):
    record = owned_record(source_id)
    data = body()
    if type(data.get("version")) is not int or data["version"] != record.version:
        raise APIError("记录已在其他页面更新，请重新打开后编辑。", 409, "version_conflict")
    # 数据库层同时比较版本，避免两个请求在同一时刻通过预检查。
    old_version = record.version
    result = db.session.execute(db.update(LifeRecord).where(LifeRecord.id == record.id, LifeRecord.version == old_version).values(version=old_version + 1).execution_options(synchronize_session=False))
    if result.rowcount != 1:
        raise APIError("记录已更新，请重新打开后编辑。", 409, "version_conflict")
    record = save_record(data, record=record)
    db.session.commit()
    return {"data": record_data(record)}


@bp.delete("/records/<source_id>")
@local_required
def remove(source_id):
    record = owned_record(source_id)
    data = body()
    if type(data.get("version")) is not int or data["version"] != record.version:
        raise APIError("记录已更新，请重新打开后删除。", 409, "version_conflict")
    set_deleted(record, True, data["version"])
    db.session.commit()
    return {"data": {"deleted": True, "version": record.version, "recoverable": True}}


def set_deleted(record, deleted, expected_version):
    from ..services.record_documents import millis, record_document
    changed = db.session.execute(db.update(LifeRecord).where(LifeRecord.id == record.id, LifeRecord.version == expected_version).values(version=expected_version + 1).execution_options(synchronize_session=False))
    if changed.rowcount != 1:
        raise APIError("记录已变化，请刷新后重试。", 409, "version_conflict")
    record.version = expected_version + 1
    record.is_deleted = deleted
    record.updated_at = now()
    payload = {**record.payload, "deletedAt": millis(record.updated_at) if deleted else None}
    if payload.get("androidDocument"):
        payload["androidDocument"] = {**payload["androidDocument"], "updatedAt": millis(record.updated_at), "deletedAt": payload["deletedAt"]}
    record.payload = payload
    if payload.get("androidDocument"):
        record.payload = {**record.payload, "androidDocument": record_document(record)}


@bp.post("/records/<source_id>/restore")
@local_required
def restore(source_id):
    record = owned_record(source_id, include_deleted=True)
    value = body()
    if type(value.get("version")) is not int or value["version"] != record.version:
        raise APIError("回收站记录已变化，请刷新后重试。", 409, "version_conflict")
    if record.is_deleted:
        set_deleted(record, False, value["version"])
    db.session.commit()
    return {"data": record_data(record)}



@bp.post("/photos")
@local_required
def upload():
    file = request.files.get("photo")
    if not file:
        raise APIError("请选择一张图片。")
    raw = file.read(50 * 1024 * 1024 + 1)
    if len(raw) > 50 * 1024 * 1024:
        raise APIError("单张照片不能超过 50 MB。", 413)
    photo = make_photo(raw)
    db.session.add(photo)
    db.session.commit()
    return {"data": {"uri": f"/api/v1/photos/{photo.id}"}}, 201


def make_photo(raw):
    try:
        # 对齐 Android：验证图片，但不重编码原图；元信息描述原字节。
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", Image.DecompressionBombWarning)
            with Image.open(BytesIO(raw)) as original:
                if original.format not in {"JPEG", "PNG", "WEBP"} or original.width * original.height > 100_000_000:
                    raise APIError("请上传不超过 1 亿像素的 JPEG、PNG 或 WebP。")
                content_type = Image.MIME[original.format]
                original.verify()
        preview = thumbnail(raw)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise APIError("图片无法读取，请选择有效照片。") from None
    photo = Photo(user_id=g.owner.id, content_type=content_type, data=raw, thumbnail_data=preview)
    return photo


def thumbnail(raw):
    output = BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", Image.DecompressionBombWarning)
        with Image.open(BytesIO(raw)) as source:
            if source.width * source.height > 100_000_000:
                raise ValueError('Image exceeds the pixel limit')
            source.draft('RGB', (320, 320))
            source.thumbnail((320, 320), Image.Resampling.LANCZOS)
            ImageOps.exif_transpose(source).convert('RGB').save(output, 'JPEG', quality=65, optimize=True)
    data = output.getvalue()
    if len(data) > 60_000:
        raise ValueError('Thumbnail exceeds the storage limit')
    return data


@bp.post("/photos/batch")
@local_required
def upload_batch():
    files = request.files.getlist("photos")
    if not 1 <= len(files) <= 10:
        raise APIError("请选择 1—10 张照片。")
    key = request.form.get('requestKey')
    if key:
        try:
            if str(UUID(key)) != key:
                raise ValueError
        except ValueError:
            raise APIError('照片上传编号无效。', code='requestKey') from None
    photos = []
    # 全部验证成功后才提交；中途任何失败均回滚，不留下部分导入。
    inputs = []
    for index, file in enumerate(files):
        raw = file.read(50 * 1024 * 1024 + 1)
        if len(raw) > 50 * 1024 * 1024:
            raise APIError("单张照片不能超过 50 MB。", 413)
        source = f'web-upload:{key}:{index}:{len(files)}' if key else None
        inputs.append((raw, source))
    previous = {}
    if key:
        previous = {p.source_id: p for p in db.session.scalars(select(Photo).where(
            Photo.user_id == g.owner.id, Photo.source_id.startswith(f'web-upload:{key}:'),
        ).with_for_update())}
        if previous and set(previous) != {source for _, source in inputs}:
            raise APIError('照片上传编号已用于其他文件。', 409, 'idempotency_conflict')
    for raw, source in inputs:
        if source in previous:
            photo = previous[source]
            if sha256(photo.data).digest() != sha256(raw).digest():
                raise APIError('照片上传编号已用于其他文件。', 409, 'idempotency_conflict')
        else:
            photo = make_photo(raw)
            photo.source_id = source
        photos.append(photo)
    db.session.add_all(photos)
    db.session.commit()
    return {"data": {"photos": [{"uri": f"/api/v1/photos/{photo.id}"} for photo in photos]}}, 201


@bp.get("/photos/<photo_id>")
@local_required
def photo(photo_id):
    item = db.session.get(Photo, photo_id)
    if not item or item.user_id != g.owner.id:
        raise APIError("照片不存在。", 404)
    if not item.data:
        raise APIError("照片原图正在同步，请稍后重试。", 409, "original_not_ready")
    return send_file(BytesIO(item.data), mimetype=item.content_type, max_age=0)


@bp.get("/photos/<photo_id>/thumbnail")
@local_required
def photo_thumbnail(photo_id):
    item = db.session.get(Photo, photo_id)
    if not item or item.user_id != g.owner.id:
        raise APIError("照片不存在。", 404)
    if item.thumbnail_data is None and not db.session.scalar(select(func.length(Photo.data)).where(Photo.id == item.id)):
        raise APIError("照片原图正在同步，请稍后重试。", 409, "original_not_ready")
    try:
        data = item.thumbnail_data or thumbnail(item.data)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise APIError("照片不存在。", 404) from None
    return send_file(BytesIO(data), mimetype='image/jpeg', max_age=0)
