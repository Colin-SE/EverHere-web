"""F2—F3：普通用户整理，受分配管理员审核，服务端按当前版本制作。"""
from io import BytesIO

from flask import Blueprint, g, request, send_file, current_app
from sqlalchemy import select

from ..extensions import db
from ..models import now
from ..models_workflow import Memoir, MemoirRevision, MemoirAsset, MemoirJob
from ..security import APIError, body, member_required, admin_required
from ..i18n import translate
from ..services import memoir_pdf
from ..services.memoir_jobs import queue_job, run_job, wake_worker
from ..services.memoirs import active_revision, assigned, check_version, freeze, get_memoir, memoir_data, normalise_draft, touch

bp = Blueprint('memoirs', __name__, url_prefix='/api/v1')


@bp.get('/memoirs')
@member_required
def listing():
    items = db.session.scalars(select(Memoir).where(Memoir.owner_id == g.member.id).order_by(Memoir.updated_at.desc()))
    return {'data': {'memoirs': [memoir_data(item) for item in items]}}


@bp.post('/memoirs')
@member_required
def create():
    title, theme, chapters = normalise_draft(body())
    item = Memoir(owner_id=g.member.id, space_id=g.owner.id, title=title, theme=theme, draft=chapters)
    db.session.add(item)
    db.session.commit()
    return {'data': memoir_data(item, detail=True)}, 201


@bp.get('/memoirs/<memoir_id>')
@member_required
def detail(memoir_id):
    return {'data': memoir_data(get_memoir(memoir_id), detail=True)}


@bp.put('/memoirs/<memoir_id>')
@member_required
def update(memoir_id):
    data = body()
    item = get_memoir(memoir_id, lock=True)
    check_version(item, data)
    if item.state not in ('draft', 'returned'):
        raise APIError('只有草稿或退回稿可以修改。', 409, 'invalid_state')
    if item.space_id != g.owner.id:
        raise APIError('请在创建回忆录的原档案中选材。', 409)
    item.title, item.theme, item.draft = normalise_draft(data)
    touch(item)
    db.session.commit()
    return {'data': memoir_data(item, detail=True)}


@bp.post('/memoirs/<memoir_id>/submit')
@member_required
def submit(memoir_id):
    data = body()
    item = get_memoir(memoir_id, lock=True)
    check_version(item, data)
    if item.state not in ('draft', 'returned'):
        raise APIError('此状态不能重复提交。', 409, 'invalid_state')
    if data.get('authoriseMaterials') is not True:
        raise APIError('请明确确认将所选文字、日期、地点和照片提供给制作管理员。', code='authoriseMaterials')
    freeze(item)
    db.session.commit()
    return {'data': memoir_data(item, detail=True)}, 201


@bp.get('/admin/memoirs')
@admin_required
def queue():
    wake_worker()
    rows = db.session.execute(select(Memoir, MemoirRevision).join(MemoirRevision, (MemoirRevision.memoir_id == Memoir.id) & (MemoirRevision.number == Memoir.revision_number)).where(
        Memoir.owner_id != g.member.id, (MemoirRevision.reviewer_id == g.member.id) | ((MemoirRevision.reviewer_id.is_(None)) & (Memoir.state == 'submitted'))).order_by(Memoir.updated_at))
    # 未领取任务只显示队列元数据，不开放正文与图片。
    return {'data': {'memoirs': [({'id': m.id, 'state': m.state, 'version': m.version, 'revisionId': r.id, 'revisionNumber': r.number, 'reviewerId': None} if not r.reviewer_id else memoir_data(m, staff=True)) for m, r in rows]}}


@bp.post('/admin/memoirs/<memoir_id>/claim')
@admin_required
def claim(memoir_id):
    data = body()
    item = get_memoir(memoir_id, admin=True, lock=True)
    revision = check_version(item, data, revision=True)
    if item.owner_id == g.member.id or item.state != 'submitted' or revision.reviewer_id:
        raise APIError('此任务无法领取，请刷新队列。', 409, 'invalid_state')
    # 条件写入保证同一修订只会被领取一次，不能依赖页面按钮或预读取。
    claimed = db.session.execute(db.update(MemoirRevision).where(
        MemoirRevision.id == revision.id, MemoirRevision.reviewer_id.is_(None),
        MemoirRevision.state == 'submitted'
    ).values(reviewer_id=g.member.id))
    if claimed.rowcount != 1:
        raise APIError('此任务无法领取，请刷新队列。', 409, 'invalid_state')
    touch(item)
    db.session.commit()
    return {'data': memoir_data(item, detail=True, staff=True)}


@bp.get('/admin/memoirs/<memoir_id>')
@admin_required
def review_detail(memoir_id):
    item = get_memoir(memoir_id, admin=True)
    revision = active_revision(item)
    assigned(item, revision)
    job = db.session.get(MemoirJob, revision.id)
    if job and job.state in ('queued', 'running'):
        wake_worker()
    return {'data': memoir_data(item, detail=True, staff=True)}


@bp.post('/admin/memoirs/<memoir_id>/review')
@admin_required
def review(memoir_id):
    data = body()
    item = get_memoir(memoir_id, admin=True, lock=True)
    revision = check_version(item, data, revision=True)
    assigned(item, revision)
    if item.state != 'submitted':
        raise APIError('只有待审核稿件可以审核。', 409, 'invalid_state')
    decision = data.get('decision')
    if decision not in ('approve', 'return'):
        raise APIError('请选择通过或退回。')
    reason = data.get('reason', '')
    if not isinstance(reason, str) or len(reason) > 2000 or (decision == 'return' and not reason.strip()):
        raise APIError('退回时必须填写原因，最多 2000 字。', code='reason')
    item.state = revision.state = 'approved' if decision == 'approve' else 'returned'
    revision.reason, revision.reviewed_at = reason.strip(), now()
    touch(item)
    db.session.commit()
    return {'data': memoir_data(item, detail=True, staff=True)}


@bp.post('/admin/memoirs/<memoir_id>/generate')
@admin_required
def generate(memoir_id):
    data = body()
    item = get_memoir(memoir_id, admin=True, lock=True)
    revision = active_revision(item)
    assigned(item, revision)
    job = db.session.get(MemoirJob, revision.id)
    if data.get('revisionId') == revision.id and job and job.state in ('queued', 'running', 'succeeded'):
        if job.state != 'succeeded':
            wake_worker()
        return {'data': memoir_data(item, detail=True, staff=True)}, 200 if job.state == 'succeeded' else 202
    revision = check_version(item, data, revision=True)
    if item.state != 'approved':
        raise APIError('只能制作当前审核通过的版本。', 409, 'invalid_state')
    count = len(revision.snapshot['chapters'])
    order, font = data.get('chapterOrder', list(range(count))), data.get('fontSize', 12)
    if not isinstance(order, list) or any(type(i) is not int for i in order) or sorted(order) != list(range(count)):
        raise APIError('排版顺序须完整包含所有章节且不得重复。')
    if type(font) is not int or not 10 <= font <= 16:
        raise APIError('字号须为 10—16。')
    layout = {'chapterOrder': order, 'fontSize': font}
    queue_job(item, revision, layout)
    if data.get('background') is True:
        wake_worker()
        return {'data': memoir_data(item, detail=True, staff=True)}, 202
    # 保留既有客户端的同步请求契约，并使用同一份持久任务。
    run_job(revision.id)
    item = get_memoir(memoir_id, admin=True)
    revision = active_revision(item)
    if revision.render_error:
        return {'data': memoir_data(item, detail=True, staff=True), 'error': {'code': 'render_failed', 'message': translate(revision.render_error)}}, 422
    return {'data': memoir_data(item, detail=True, staff=True)}


def accessible_revision(memoir_id):
    item = get_memoir(memoir_id, admin=True)
    revision = active_revision(item)
    if item.owner_id != g.member.id:
        if g.member.role != 'admin':
            raise APIError('回忆录不存在。', 404)
        assigned(item, revision)
    if not revision:
        raise APIError('尚未提交回忆录。', 404)
    return item, revision


@bp.get('/memoirs/<memoir_id>/assets/<asset_id>')
@member_required
def image(memoir_id, asset_id):
    _, revision = accessible_revision(memoir_id)
    asset = db.session.get(MemoirAsset, asset_id)
    if not asset or asset.revision_id != revision.id or asset.kind != 'photo':
        raise APIError('素材不存在。', 404)
    return send_file(BytesIO(asset.data), mimetype=asset.content_type, max_age=0)


@bp.get('/memoirs/<memoir_id>/preview.pdf')
@member_required
def preview(memoir_id):
    item, revision = accessible_revision(memoir_id)
    asset = db.session.scalar(select(MemoirAsset).where(MemoirAsset.revision_id == revision.id, MemoirAsset.kind == 'final'))
    if item.state != 'ready' or not asset:
        raise APIError('成品尚未制作完成。', 409, 'not_ready')
    # 旧版本曾把完整正文当预览保存。始终从成品重新提取样张，旧数据也不泄露全文。
    try:
        sample = memoir_pdf.sample_pdf(asset.data)
    except Exception as error:
        current_app.logger.error('样张读取失败：%s', type(error).__name__)
        raise APIError('预览暂时无法读取，请稍后重试。', 503, 'preview_unavailable') from None
    return send_file(BytesIO(sample), mimetype='application/pdf', as_attachment=False, download_name='memoir-preview.pdf', max_age=0)
