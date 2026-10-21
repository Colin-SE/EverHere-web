"""Android 普通归档入口，不保留旧 Web 保险箱导出或旧格式接口。"""
from flask import Blueprint, g, request, send_file
from io import BytesIO
from sqlalchemy import select
from ..extensions import db
from ..models import ArchiveJob

from ..security import APIError, body, local_required
from ..services.android_archive import export_android
from ..services.archive import merge, prepare

bp = Blueprint('archive', __name__, url_prefix='/api/v1/archive')


@bp.get('/export')
@local_required
def export():
    if request.args.get('includePrivate') == 'true':
        raise APIError('旧保险箱功能和受保护备份已删除。', 404)
    return {'data': export_android()}


@bp.post('/preview')
@local_required
def preview():
    _, result = prepare(body().get('archive'))
    return {'data': result}


@bp.post('/import')
@local_required
def importing():
    data = body()
    return {'data': merge(data.get('archive'), data.get('fingerprint'), data.get('targetFingerprint'), data.get('copyConflicts') is True, data.get('acceptMissingPhotos') is True)}


@bp.get('/export.zip')
@local_required
def zipped():
    from ..services.archive_files import export_zip
    return send_file(BytesIO(export_zip()), mimetype='application/zip', as_attachment=True, download_name='everhere-ordinary.zip', max_age=0)


@bp.post('/files/preview')
@local_required
def file_preview():
    from ..services.archive_files import MAX_ARCHIVE, preview_file
    source = request.files.get('archive')
    if not source:
        raise APIError('请选择普通 JSON 或 ZIP。')
    return {'data': preview_file(source.read(MAX_ARCHIVE+1))}


@bp.get('/jobs')
@local_required
def jobs():
    from ..services.archive_files import describe
    values = db.session.scalars(select(ArchiveJob).where(ArchiveJob.owner_id == g.owner.id, ArchiveJob.committed_at.is_(None)).order_by(ArchiveJob.created_at.desc()))
    return {'data': {'jobs': [describe(job) for job in values]}}


@bp.get('/jobs/<identifier>')
@local_required
def job_preview(identifier):
    from ..services.archive_files import describe, get_job
    return {'data': describe(get_job(identifier))}


@bp.post('/jobs/<identifier>/confirm')
@local_required
def job_confirm(identifier):
    from ..services.archive_files import confirm_job
    return {'data': confirm_job(identifier, body())}


@bp.delete('/jobs/<identifier>')
@local_required
def job_discard(identifier):
    from ..services.archive_files import get_job, stage_path
    job = get_job(identifier)
    try:
        stage_path(job).unlink(missing_ok=True)
    except OSError:
        raise APIError('暂存尚未清理，请稍后重试。', 503) from None
    if not job.committed_at:
        db.session.delete(job)
    db.session.commit()
    return {'data': {'discarded': True}}


@bp.post('/jobs/<identifier>/refresh')
@local_required
def job_refresh(identifier):
    from ..services.archive_files import get_job, read_job, describe
    from ..services.archive import local_fingerprint, plan
    job = get_job(identifier)
    if job.committed_at:
        raise APIError('本次恢复已经完成。', 409)
    archive, data, originals = read_job(job)
    _, summary, _ = plan(data)
    job.summary = {**summary, 'kind': archive['manifest']['kind'], 'missingOriginals': archive['manifest']['missingOriginals']}
    job.target_hash = local_fingerprint()
    db.session.commit()
    return {'data': describe(job)}
