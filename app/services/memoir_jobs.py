"""回忆录生成任务持久化。任务超时后可以重领，旧执行尝试无权提交。"""
from datetime import timedelta
from hashlib import sha256
from threading import Event, Lock, Thread

from flask import current_app
from sqlalchemy import or_, select

from ..extensions import db
from ..models import now
from ..models_workflow import Memoir, MemoirAsset, MemoirJob, MemoirRevision
from . import memoir_pdf
from .memoirs import touch

LEASE = timedelta(minutes=10)
RENDER_ERROR = '生成失败，已保留审核材料，请检查图片或版式后重试。'
runner_lock = Lock()
pending_wakeup = Event()


def queue_job(item, revision, layout):
    job = db.session.get(MemoirJob, revision.id)
    if job and job.state in ('queued', 'running', 'succeeded'):
        return job
    if job is None:
        job = MemoirJob(revision_id=revision.id, state='queued', attempt=0)
        db.session.add(job)
    job.state, job.updated_at = 'queued', now()
    revision.layout, revision.render_error = layout, ''
    touch(item)
    db.session.commit()
    return job


def run_job(revision_id):
    job = db.session.get(MemoirJob, revision_id)
    if not job:
        return False
    attempt = job.attempt + 1
    stamp = now()
    updated = db.session.execute(db.update(MemoirJob).where(
        MemoirJob.revision_id == revision_id, MemoirJob.attempt == job.attempt,
        or_(MemoirJob.state == 'queued', (MemoirJob.state == 'running') & (MemoirJob.updated_at <= stamp - LEASE)),
    ).values(state='running', attempt=attempt, updated_at=stamp))
    db.session.commit()
    if updated.rowcount != 1:
        return False

    revision = db.session.get(MemoirRevision, revision_id)
    assets = {asset.id: asset for asset in db.session.scalars(select(MemoirAsset).where(
        MemoirAsset.revision_id == revision_id, MemoirAsset.kind == 'photo'))}
    snapshot, layout = revision.snapshot, revision.layout
    # 装载选中的图片后结束读取事务，渲染期间不持有数据库锁。
    for asset in assets.values():
        db.session.expunge(asset)
    db.session.rollback()
    try:
        final = memoir_pdf.render_pdf(snapshot, assets, layout)
        preview = memoir_pdf.sample_pdf(final)
        succeeded = True
    except Exception as error:
        current_app.logger.error('回忆录制作失败：%s', type(error).__name__)
        succeeded = False

    job = db.session.scalar(select(MemoirJob).where(MemoirJob.revision_id == revision_id)
                            .with_for_update().execution_options(populate_existing=True))
    if job.state != 'running' or job.attempt != attempt:
        db.session.rollback()
        return False
    revision = db.session.get(MemoirRevision, revision_id)
    item = db.session.scalar(select(Memoir).where(Memoir.id == revision.memoir_id).with_for_update())
    if item.state != 'approved' or item.revision_number != revision.number:
        succeeded = False
    if succeeded:
        for kind, data in (('final', final), ('preview', preview)):
            db.session.add(MemoirAsset(revision_id=revision.id, kind=kind, content_type='application/pdf',
                                       checksum=sha256(data).hexdigest(), data=data))
        item.state = revision.state = 'ready'
    revision.render_error = '' if succeeded else RENDER_ERROR
    job.state, job.updated_at = ('succeeded' if succeeded else 'failed'), now()
    touch(item)
    db.session.commit()
    return succeeded


def wake_worker():
    app = current_app._get_current_object()
    if app.testing:
        return
    pending_wakeup.set()
    if not runner_lock.acquire(blocking=False):
        return

    def drain():
        try:
            with app.app_context():
                while True:
                    pending_wakeup.clear()
                    revision_id = db.session.scalar(select(MemoirJob.revision_id).where(
                        or_(MemoirJob.state == 'queued',
                            (MemoirJob.state == 'running') & (MemoirJob.updated_at <= now() - LEASE)),
                    ).order_by(MemoirJob.updated_at).limit(1))
                    if not revision_id:
                        break
                    run_job(revision_id)
                    db.session.remove()
        except Exception as error:
            app.logger.error('回忆录任务执行中断：%s', type(error).__name__)
        finally:
            runner_lock.release()
            if pending_wakeup.is_set():
                with app.app_context():
                    wake_worker()

    Thread(target=drain, daemon=True, name='memoir-worker').start()
