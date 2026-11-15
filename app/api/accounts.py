"""相册、回忆录与商城共用的网站账户；保留显式认领已有空间。"""
import re
import secrets

from flask import Blueprint, g, session, current_app, request
from flask_login import login_user, logout_user
from sqlalchemy import select
from werkzeug.security import generate_password_hash, check_password_hash

from ..extensions import db, limiter
from ..models import LocalSpace, now
from ..models_identity import DeviceSession
from ..models_workflow import Member, SpaceOwnership
from ..security import APIError, body, csrf_token, member_required
from ..services import identity

bp = Blueprint('accounts', __name__, url_prefix='/api/v1/accounts')
# 不存在的邮箱也计算哈希验证，避免显著的密码耗时差异。
DUMMY_HASH = generate_password_hash(secrets.token_urlsafe(32))


@bp.before_request
def identity_request_bound():
    request.max_content_length = 16384


def account_data(member):
    return {'id': member.id, 'name': member.name, 'email': member.email, 'role': member.role}


def credentials(data):
    email, password = data.get('email'), data.get('password')
    if not isinstance(email, str) or len(email) > 254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
        raise APIError('请填写有效邮箱。', code='email')
    if not isinstance(password, str) or not 10 <= len(password) <= 128:
        raise APIError('密码须为 10—128 个字符。', code='password')
    return email.strip().lower(), password


def establish(member, space_id, auth_epoch):
    # 登录不吞并访客资料，也不丢弃返回该访客档案的凭据。
    # 仅保存已持有、尚未被任何账户认领的空间引用，不保存正文或密码。
    guest = session.get('guest_space')
    if not g.member and g.owner.id != space_id and not db.session.get(SpaceOwnership, g.owner.id):
        guest = {'id': g.owner.id, 'version': g.owner.access_version}
    session.clear()
    login_user(member)
    # 必须使用授权锁内捕获的版本；提交后重读可能错误接受刚发生的撤销。
    session['auth_epoch'] = auth_epoch
    if guest:
        session['guest_space'] = guest
    space = db.session.get(LocalSpace, space_id)
    session['space_id'], session['space_version'] = space.id, space.access_version
    session.permanent = True
    return {'data': {'member': account_data(member), 'csrfToken': csrf_token(), 'spaceId': space.id}}


@bp.post('/register')
@limiter.limit('10 per hour')
def register():
    if g.member:
        raise APIError('请先退出当前账户。', 409)
    data = body()
    email, password = credentials(data)
    if current_app.config.get('SHARED_IDENTITY_ENABLED'):
        identity.limit(request.remote_addr or 'unknown', 'browser-auth', 90, 300)
        member, space = identity.register(data.get('challengeId'), data.get('code'), password,
            data.get('name'), g.owner if data.get('claimCurrentSpace') is True else None, expected_email=email)
        return establish(member, space.id, 0), 201
    name = data.get('name', '')
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80:
        raise APIError('姓名须为 1—80 个字符。', code='name')
    if db.session.scalar(select(Member).where(Member.email == email)):
        raise APIError('该邮箱无法注册，请登录或使用其他邮箱。', 409, 'email')
    # 浏览器只能注册普通用户；管理员由受控命令行建立。
    member = Member(email=email, name=name.strip(), password_hash=generate_password_hash(password), role='user')
    db.session.add(member)
    db.session.flush()
    space = g.owner if data.get('claimCurrentSpace') is True else LocalSpace()
    db.session.add(space)
    db.session.flush()
    if db.session.get(SpaceOwnership, space.id):
        raise APIError('此档案已有账户归属，无法重复认领。', 409)
    db.session.add(SpaceOwnership(space_id=space.id, member_id=member.id))
    db.session.commit()
    return establish(member, space.id, 0), 201


@bp.post('/login')
@limiter.limit('15 per minute')
def login():
    data = body()
    email, password = credentials(data)
    if current_app.config.get('SHARED_IDENTITY_ENABLED'):
        identity.limit(request.remote_addr or 'unknown', 'browser-auth', 90, 300)
        identity.limit(email, 'login', 15, 300)
    member = db.session.scalar(select(Member).where(Member.email == email))
    valid = check_password_hash(member.password_hash if member else DUMMY_HASH, password)
    if not member or not valid:
        raise APIError('邮箱或密码不正确。', 401, 'invalid_credentials')
    # 与找回密码串行，避免哈希校验期间发生重置后仍建立旧密码会话。
    previous = member.password_hash
    member = identity.lock_member(member.id)
    if member.password_hash != previous:
        raise APIError('邮箱或密码不正确。', 401, 'invalid_credentials')
    auth_epoch = member.auth_epoch
    link = db.session.scalar(select(SpaceOwnership).where(SpaceOwnership.member_id == member.id).order_by(SpaceOwnership.space_id))
    if not link:
        space = LocalSpace()
        db.session.add(space)
        db.session.flush()
        link = SpaceOwnership(space_id=space.id, member_id=member.id)
        db.session.add(link)
        db.session.commit()
    return establish(member, link.space_id, auth_epoch)


@bp.get('/capabilities')
def capabilities():
    return {'data': {'sharedIdentity': bool(current_app.config.get('SHARED_IDENTITY_ENABLED')), 'region': 'cn'}}


@bp.get('/devices')
@member_required
def devices():
    identity.enabled()
    rows = db.session.scalars(select(DeviceSession).where(
        DeviceSession.member_id == g.member.id, DeviceSession.revoked.is_(False),
        DeviceSession.refresh_expires_at > now(),
    ).order_by(DeviceSession.created_at.desc(), DeviceSession.id))
    return {'data': {'devices': [{'id': row.id, 'name': row.device_name,
                                 'createdAt': identity.iso(row.created_at),
                                 'expiresAt': identity.iso(row.refresh_expires_at)} for row in rows]}}


@bp.delete('/devices/<device_id>')
@member_required
def revoke_device(device_id):
    identity.enabled()
    device = db.session.scalar(select(DeviceSession).where(
        DeviceSession.member_id == g.member.id, DeviceSession.id == device_id,
    ).with_for_update())
    if not device:
        raise APIError('设备会话不存在。', 404, 'not_found')
    device.revoked, device.rotation_receipt = True, None
    db.session.commit()
    return {'data': {'revoked': True}}


@bp.post('/code')
def code():
    identity.enabled()
    identity.limit(request.remote_addr or 'unknown', 'browser-auth', 90, 300)
    data = body()
    return {'data': identity.request_code(data.get('email'), data.get('purpose'))}


@bp.post('/reset-password')
def reset_password():
    identity.enabled()
    identity.limit(request.remote_addr or 'unknown', 'browser-auth', 90, 300)
    data = body()
    return {'data': identity.reset_password(data.get('challengeId'), data.get('code'), data.get('password'),
        expected_email=identity.email_address(data.get('email')))}


@bp.post('/logout')
@member_required
def logout():
    guest = session.get('guest_space')
    logout_user()
    session.clear()
    if isinstance(guest, dict):
        space = db.session.get(LocalSpace, guest.get('id'))
        if space and space.access_version == guest.get('version') and not db.session.get(SpaceOwnership, space.id):
            session['space_id'], session['space_version'] = space.id, space.access_version
    return {'data': {'loggedOut': True, 'csrfToken': csrf_token()}}
