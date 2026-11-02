"""本机空间与 CSRF；不再保留旧版独立账户或保险箱授权。"""
import secrets
from functools import wraps

from flask import g, request, session

from .extensions import db
from .models import LocalSpace
from .models_workflow import SpaceOwnership
from flask_login import current_user
from sqlalchemy import select


class APIError(Exception):
    def __init__(self, message, status=400, code='validation_error'):
        self.message, self.status, self.code = message, status, code


def csrf_token():
    if 'csrf' not in session:
        session['csrf'] = secrets.token_urlsafe(32)
    return session['csrf']


def load_user():
    if request.path.startswith('/static/') or request.path == '/health':
        # 静态资源不加载登录会话，避免并发资源响应写回过时的身份/CSRF Cookie。
        g.member = g.user = g.owner = None
        return
    g.member = current_user._get_current_object() if current_user.is_authenticated else None
    g.user = {'id': g.member.id, 'name': g.member.name, 'email': g.member.email, 'role': g.member.role} if g.member else None
    owner_id = session.get('space_id')
    g.owner = db.session.get(LocalSpace, owner_id) if owner_id else None
    # 已归入账户的空间，旧访客 Cookie 立即失去权限；登录也不会自动认领访客资料。
    ownership = db.session.get(SpaceOwnership, owner_id) if owner_id else None
    if ownership and (not g.member or ownership.member_id != g.member.id):
        g.owner = None
    if g.member and not g.owner:
        link = db.session.scalar(select(SpaceOwnership).where(SpaceOwnership.member_id == g.member.id).order_by(SpaceOwnership.space_id))
        if link:
            g.owner = db.session.get(LocalSpace, link.space_id)
            session['space_id'] = g.owner.id
            session['space_version'] = g.owner.access_version
    if g.owner and session.get('space_version') != g.owner.access_version:
        session.pop('space_id', None)
        session.pop('space_version', None)
        g.owner = None
    if g.owner is None:
        g.owner = LocalSpace()
        db.session.add(g.owner)
        db.session.flush()
        if g.member:
            db.session.add(SpaceOwnership(space_id=g.owner.id, member_id=g.member.id))
        db.session.commit()
        session['space_id'] = g.owner.id
        session['space_version'] = g.owner.access_version
    session.permanent = True
    if request.path.startswith('/api/') and request.method not in ('GET', 'HEAD', 'OPTIONS'):
        token = request.headers.get('X-CSRF-Token', '')
        if not session.get('csrf') or not secrets.compare_digest(token, session['csrf']):
            raise APIError('页面验证已过期，请刷新后重试。', 403, 'csrf_error')
        # 同一空间的写请求在 MySQL 内串行，预览指纹与提交不会跨过另一笔本机写入。
        db.session.execute(select(LocalSpace).where(LocalSpace.id == g.owner.id).with_for_update()).scalar_one()


def local_required(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapped


def member_required(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        if not g.member:
            raise APIError('请先登录账户。', 401, 'login_required')
        return func(*args, **kwargs)
    return wrapped


def admin_required(func):
    @wraps(func)
    @member_required
    def wrapped(*args, **kwargs):
        if g.member.role != 'admin':
            raise APIError('此操作需要管理员权限。', 403, 'admin_required')
        return func(*args, **kwargs)
    return wrapped


def body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise APIError('请求内容必须是 JSON 对象。')
    return data
