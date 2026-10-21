"""本机空间与 CSRF；不再保留旧版独立账户或保险箱授权。"""
import secrets
from functools import wraps

from flask import g, request, session

from .extensions import db
from .models import LocalSpace
from sqlalchemy import select


class APIError(Exception):
    def __init__(self, message, status=400, code='validation_error'):
        self.message, self.status, self.code = message, status, code


def csrf_token():
    if 'csrf' not in session:
        session['csrf'] = secrets.token_urlsafe(32)
    return session['csrf']


def load_user():
    g.user = None
    if request.path.startswith('/static/') or request.path == '/health':
        g.owner = None
        return
    owner_id = session.get('space_id')
    g.owner = db.session.get(LocalSpace, owner_id) if owner_id else None
    if g.owner and session.get('space_version') != g.owner.access_version:
        session.clear()
        g.owner = None
    if g.owner is None:
        session.clear()
        g.owner = LocalSpace()
        db.session.add(g.owner)
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


def body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise APIError('请求内容必须是 JSON 对象。')
    return data
