"""兼容现有 Android /v1/auth 协议；不接受浏览器 Cookie 授权。"""
from flask import Blueprint, request, jsonify
from werkzeug.exceptions import HTTPException
from sqlalchemy import select

from ..extensions import db
from ..models import now
from ..models_identity import DeviceSession
from ..security import APIError, body
from ..services import identity as service

bp = Blueprint('mobile_identity', __name__, url_prefix='/v1/auth')


@bp.before_request
def guard():
    service.enabled()
    request.max_content_length = 16384
    if request.headers.get('X-Everhere-Region') != 'cn':
        service.fail('region_mismatch')
    if request.content_length is not None and request.content_length > 16384:
        service.fail('request_too_large', 413)
    service.limit(request.remote_addr or 'unknown', 'auth-http', 90, 300)


@bp.errorhandler(APIError)
def api_error(error):
    db.session.rollback()
    return jsonify(error=error.code), error.status


@bp.errorhandler(HTTPException)
def http_error(error):
    db.session.rollback()
    return jsonify(error='request_too_large' if error.code == 413 else 'temporarily_unavailable'), error.code


def actor():
    authorization = request.headers.get('Authorization', '')
    if not authorization.startswith('Bearer '):
        service.fail('unauthorized', 401)
    return service.authenticate(authorization[7:])


@bp.post('/code')
def code():
    data = body()
    return service.request_code(data.get('email'), data.get('purpose'))


@bp.post('/register')
def register():
    data = body()
    member, _ = service.register(data.get('challengeId'), data.get('code'), data.get('password'))
    return {'userId': member.id, 'email': member.email, 'region': 'cn'}, 201


@bp.post('/reset-password')
def reset():
    data = body()
    return service.reset_password(data.get('challengeId'), data.get('code'), data.get('password'))


@bp.post('/login')
def login():
    data = body()
    return service.login(data.get('email'), data.get('password'), data.get('installationId'), data.get('deviceName'))


@bp.post('/refresh')
def refresh():
    data = body()
    return service.refresh(data.get('refreshToken'), data.get('installationId'), data.get('operationId'))


@bp.get('/me')
def me():
    member, device = actor()
    return dict(userId=member.id, sessionId=device.id, email=member.email, region='cn')


@bp.get('/sessions')
def sessions():
    member, device = actor()
    rows = db.session.scalars(select(DeviceSession).where(DeviceSession.member_id == member.id, DeviceSession.revoked.is_(False), DeviceSession.refresh_expires_at > now()).order_by(DeviceSession.created_at.desc(), DeviceSession.id)).all()
    return {'sessions': [dict(sessionId=row.id, deviceName=row.device_name, createdAt=service.iso(row.created_at), expiresAt=service.iso(row.refresh_expires_at), current=row.id == device.id) for row in rows]}


@bp.post('/logout')
def logout():
    _, device = actor()
    device.revoked, device.rotation_receipt = True, None
    db.session.commit()
    return {'revoked': True}


@bp.post('/logout-all')
def logout_all():
    member, _ = actor()
    service.revoke_all(member)
    db.session.commit()
    return {'revoked': True}


@bp.post('/revoke-session')
def revoke_session():
    data = body()
    target = service.uuid(data.get('sessionId'))
    member, _ = actor()
    device = db.session.scalar(select(DeviceSession).where(DeviceSession.id == target, DeviceSession.member_id == member.id).with_for_update())
    if device:
        device.revoked, device.rotation_receipt = True, None
    db.session.commit()
    return {'revoked': True}


@bp.post('/change-password')
def change_password():
    from werkzeug.security import check_password_hash, generate_password_hash
    data = body()
    encoded = generate_password_hash(service.password(data.get('newPassword')))
    # 先计数，再取得授权锁，避免限流提交意外释放授权锁。
    service.limit(request.remote_addr or 'unknown', 'change-password', 10, 300)
    member, _ = actor()
    old = data.get('oldPassword')
    if not isinstance(old, str) or len(old) > 128 or not check_password_hash(member.password_hash, old):
        service.fail('invalid_credentials', 401)
    member.password_hash = encoded
    service.revoke_all(member)
    db.session.commit()
    return {'changed': True}


@bp.post('/delete-account')
@bp.post('/deletion-status')
@bp.post('/deletion-ack')
def deletion_not_available():
    # 现有 Web 商城/回忆录的保留与删除策略尚未设计，绝不报告已删除。
    service.fail('temporarily_unavailable', 503)
