"""Web Cookie 与 Android Bearer 共用 members；不访问相册和同步资料。"""
import base64
import hashlib
import hmac
import json
import re
import secrets
import smtplib
import ssl
from datetime import timedelta
from email.message import EmailMessage
from uuid import UUID, uuid4

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app
from sqlalchemy import select, update, case
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from ..models import LocalSpace, now
from ..models_workflow import Member, SpaceOwnership
from ..models_identity import EmailChallenge, DeviceSession, UsedRefresh, IdentityLimit
from ..security import APIError

DUMMY_HASH = generate_password_hash(secrets.token_urlsafe(32))


def fail(code, status=400):
    messages = {
        'invalid_code': '验证码不正确、已过期或已使用。输入已保留，可重新获取验证码。',
        'mail_unavailable': '验证码邮件暂时无法发送，请稍后重试。',
        'try_later': '尝试过于频繁，请稍后再试。',
        'password_length': '新密码须为 12—128 个字符。',
        'invalid_email': '请填写有效邮箱。',
        'invalid_credentials': '邮箱或密码不正确。',
        'service_not_configured': '账号服务尚未配置，请稍后再试。',
    }
    raise APIError(messages.get(code, '账户操作未完成，请检查输入或稍后重试。'), status, code)


def enabled():
    if not current_app.config.get('SHARED_IDENTITY_ENABLED'):
        fail('service_not_configured', 503)


def uuid(value):
    try:
        if not isinstance(value, str) or str(UUID(value)) != value:
            raise ValueError()
        return value
    except ValueError:
        fail('invalid_id')


def email_address(value):
    if not isinstance(value, str):
        fail('invalid_email')
    value = value.strip().lower()
    if len(value) > 254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value) or any(ord(c) < 32 for c in value):
        fail('invalid_email')
    return value


def password(value):
    if not isinstance(value, str) or not 12 <= len(value) <= 128:
        fail('password_length')
    return value


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def mac(*values):
    key = bytes.fromhex(current_app.config['IDENTITY_SECRET'])
    return hmac.new(key, json.dumps(['cn', *values], ensure_ascii=True, separators=(',', ':')).encode(), hashlib.sha256).hexdigest()


def receipt_cipher():
    key = bytes.fromhex(mac('rotation-receipt-key'))
    return Fernet(base64.urlsafe_b64encode(key))


def limit(source, purpose, count, seconds=3600):
    """数据库原子计数，跨 worker 生效；失败次数独立提交。"""
    key, clock = mac('limit', purpose, source), now()
    table = IdentityLimit.__table__
    values = dict(key=key, hits=1, resets_at=clock + timedelta(seconds=seconds))
    if db.engine.dialect.name == 'mysql':
        from sqlalchemy.dialects.mysql import insert
        statement = insert(table).values(**values)
        statement = statement.on_duplicate_key_update(
            hits=case((table.c.resets_at <= clock, 1), else_=table.c.hits + 1),
            resets_at=case((table.c.resets_at <= clock, values['resets_at']), else_=table.c.resets_at))
    else:
        from sqlalchemy.dialects.sqlite import insert
        statement = insert(table).values(**values).on_conflict_do_update(index_elements=['key'], set_={
            'hits': case((table.c.resets_at <= clock, 1), else_=table.c.hits + 1),
            'resets_at': case((table.c.resets_at <= clock, values['resets_at']), else_=table.c.resets_at)})
    db.session.execute(statement)
    row = db.session.get(IdentityLimit, key, populate_existing=True)
    hits = row.hits
    db.session.commit()
    if hits > count:
        fail('try_later', 429)
    return key


def send_mail(address, purpose, code):
    # 仅测试通过回调接收验证码；生产没有日志/控制台降级。
    callback = current_app.config.get('IDENTITY_TEST_MAILER')
    if current_app.testing and callback:
        callback(address, purpose, code)
        return
    config = current_app.config
    if not all(config.get(k) for k in ('IDENTITY_SMTP_HOST', 'IDENTITY_MAIL_FROM', 'IDENTITY_SMTP_USER', 'IDENTITY_SMTP_PASSWORD')):
        fail('mail_unavailable', 503)
    message = EmailMessage()
    message['From'], message['To'] = config['IDENTITY_MAIL_FROM'], address
    message['Subject'] = 'Everhere 在场 · 邮箱验证' if purpose == 'register' else 'Everhere 在场 · 重置密码'
    message.set_content(f'你的验证码是 {code}，10 分钟内有效。请勿转发。\n如果不是你本人操作，请忽略此邮件。')
    try:
        context = ssl.create_default_context()
        if config['IDENTITY_SMTP_TLS'] == 'implicit':
            connection = smtplib.SMTP_SSL(config['IDENTITY_SMTP_HOST'], config['IDENTITY_SMTP_PORT'], timeout=10, context=context)
        else:
            connection = smtplib.SMTP(config['IDENTITY_SMTP_HOST'], config['IDENTITY_SMTP_PORT'], timeout=10)
        with connection as smtp:
            if config['IDENTITY_SMTP_TLS'] == 'starttls':
                smtp.starttls(context=context)
            smtp.login(config['IDENTITY_SMTP_USER'], config['IDENTITY_SMTP_PASSWORD'])
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException):
        fail('mail_unavailable', 503)


def request_code(address, purpose):
    enabled()
    email = email_address(address)
    if purpose not in ('register', 'reset'):
        fail('invalid_purpose')
    key = limit(email, 'mail', 3)
    # 同邮箱的所有验证码请求串行；旧信不会在新信之后重新成为有效码。
    db.session.scalar(select(IdentityLimit).where(IdentityLimit.key == key).with_for_update())
    existing = db.session.scalar(select(Member).where(Member.email == email))
    challenge = EmailChallenge(id=str(uuid4()), email=email, purpose=purpose, expires_at=now() + timedelta(minutes=10))
    code = f'{secrets.randbelow(100000000):08d}'
    challenge.code_mac = mac('code', challenge.id, email, purpose, code)
    db.session.execute(update(EmailChallenge).where(EmailChallenge.email == email, EmailChallenge.consumed.is_(False)).values(consumed=True))
    db.session.add(challenge)
    # 响应格式不泄漏账号存在性；重复注册码不能用于接管旧账号。
    if (purpose == 'register' and not existing) or (purpose == 'reset' and existing):
        send_mail(email, purpose, code)
        challenge.sent = True
    db.session.commit()
    return {'challengeId': challenge.id, 'expiresInSeconds': 600}


def consume(challenge_id, code, purpose, expected_email=None):
    challenge_id = uuid(challenge_id)
    row = db.session.scalar(select(EmailChallenge).where(EmailChallenge.id == challenge_id).with_for_update())
    if not row or row.consumed or not row.sent or row.expires_at <= now() or row.purpose != purpose or row.attempts >= 5:
        fail('invalid_code')
    row.attempts += 1
    if not isinstance(code, str) or not re.fullmatch(r'\d{8}', code) or not hmac.compare_digest(row.code_mac, mac('code', row.id, row.email, purpose, code)) or (expected_email is not None and row.email != expected_email):
        db.session.commit()
        fail('invalid_code')
    row.consumed = True
    return row.email


def register(challenge_id, code, raw_password, name=None, claim_space=None, expected_email=None):
    enabled()
    encoded = generate_password_hash(password(raw_password))
    email = consume(challenge_id, code, 'register', expected_email)
    if db.session.scalar(select(Member).where(Member.email == email)):
        db.session.commit()
        fail('account_exists', 409)
    if name is None:
        name = email.split('@')[0][:80]
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80:
        fail('invalid_name')
    member = Member(email=email, name=name.strip(), password_hash=encoded, role='user', email_verified_at=now())
    space = claim_space if claim_space is not None else LocalSpace()
    if claim_space is not None and db.session.get(SpaceOwnership, space.id):
        fail('space_already_owned', 409)
    db.session.add_all([member, space])
    db.session.flush()
    db.session.add(SpaceOwnership(space_id=space.id, member_id=member.id))
    db.session.commit()
    return member, space


def lock_member(member_id):
    member = db.session.scalar(select(Member).where(Member.id == member_id).with_for_update().execution_options(populate_existing=True))
    if not member:
        fail('unauthorized', 401)
    return member


def revoke_all(member):
    member.auth_epoch += 1
    db.session.execute(update(DeviceSession).where(DeviceSession.member_id == member.id).values(revoked=True, rotation_receipt=None))


def reset_password(challenge_id, code, raw_password, expected_email=None):
    enabled()
    encoded = generate_password_hash(password(raw_password))
    email = consume(challenge_id, code, 'reset', expected_email)
    member_id = db.session.scalar(select(Member.id).where(Member.email == email))
    if not member_id:
        fail('invalid_code')
    member = lock_member(member_id)
    member.password_hash = encoded
    member.email_verified_at = now()
    revoke_all(member)
    # 同时撤销该地址其他未使用的注册/重置码。
    db.session.execute(update(EmailChallenge).where(EmailChallenge.email == email).values(consumed=True))
    db.session.commit()
    return {'reset': True}


def iso(value):
    return value.isoformat(timespec='milliseconds') + 'Z'


def issue(member, device, fresh=False):
    access, refresh = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    device.access_hash, device.refresh_hash = digest(access), digest(refresh)
    device.access_expires_at = now() + timedelta(minutes=10)
    if fresh:
        device.refresh_expires_at = now() + timedelta(days=30)
    return dict(region='cn', userId=member.id, sessionId=device.id, email=member.email,
                accessToken=access, refreshToken=refresh, accessExpiresAt=iso(device.access_expires_at), refreshExpiresAt=iso(device.refresh_expires_at))


def login(address, raw_password, installation_id, device_name):
    enabled()
    email, installation = email_address(address), uuid(installation_id)
    if not isinstance(device_name, str) or not 1 <= len(device_name.strip()) <= 80:
        fail('invalid_device')
    limit(email, 'login', 15, 300)
    member = db.session.scalar(select(Member).where(Member.email == email))
    encoded = member.password_hash if member else DUMMY_HASH
    if not isinstance(raw_password, str) or len(raw_password) > 128 or not check_password_hash(encoded, raw_password) or not member:
        fail('invalid_credentials', 401)
    member = lock_member(member.id)
    if member.password_hash != encoded:
        fail('invalid_credentials', 401)
    device = DeviceSession(id=str(uuid4()), member_id=member.id, installation_id=installation, device_name=device_name.strip())
    result = issue(member, device, fresh=True)
    db.session.add(device)
    db.session.commit()
    return result


def bearer(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', value):
        fail('unauthorized', 401)
    return digest(value)


def authenticate(value):
    hashed = bearer(value)
    candidate = db.session.scalar(select(DeviceSession).where(DeviceSession.access_hash == hashed))
    if not candidate:
        fail('unauthorized', 401)
    member = lock_member(candidate.member_id)
    device = db.session.scalar(select(DeviceSession).where(DeviceSession.id == candidate.id).with_for_update().execution_options(populate_existing=True))
    if device.revoked or device.access_hash != hashed or device.access_expires_at <= now() or device.refresh_expires_at <= now():
        fail('unauthorized', 401)
    return member, device


def refresh(value, installation_id, operation_id):
    hashed, installation, operation = bearer(value), uuid(installation_id), uuid(operation_id)
    candidate = db.session.scalar(select(DeviceSession).where(DeviceSession.refresh_hash == hashed))
    if not candidate:
        used = db.session.get(UsedRefresh, hashed)
        candidate = db.session.get(DeviceSession, used.session_id) if used else None
    if not candidate:
        fail('unauthorized', 401)
    member = lock_member(candidate.member_id)
    device = db.session.scalar(select(DeviceSession).where(DeviceSession.id == candidate.id).with_for_update().execution_options(populate_existing=True))
    if device.revoked or device.refresh_expires_at <= now() or device.installation_id != installation:
        fail('unauthorized', 401)
    if device.refresh_hash != hashed:
        if device.previous_hash == hashed and device.rotation_id == operation and device.receipt_expires_at and device.receipt_expires_at > now() and device.rotation_receipt:
            try:
                envelope = json.loads(receipt_cipher().decrypt(device.rotation_receipt.encode(), ttl=120))
                if envelope['context'] == [device.id, installation, operation, hashed]:
                    return envelope['result']
            except (InvalidToken, ValueError, KeyError):
                pass
        device.revoked, device.rotation_receipt = True, None
        db.session.commit()
        fail('session_revoked', 401)
    if device.rotation_id == operation:
        fail('rotation_id_reused', 409)
    result = issue(member, device)
    db.session.add(UsedRefresh(token_hash=hashed, session_id=device.id))
    device.previous_hash, device.rotation_id = hashed, operation
    device.receipt_expires_at = now() + timedelta(minutes=2)
    device.rotation_receipt = receipt_cipher().encrypt(json.dumps({'context': [device.id, installation, operation, hashed], 'result': result}).encode()).decode()
    db.session.commit()
    return result
