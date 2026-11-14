"""共用身份的追加表；members 和现有资料 ID 不迁移、不重编号。"""
from .extensions import db
from .models import new_id, now


class EmailChallenge(db.Model):
    __tablename__ = 'identity_challenges'
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    email = db.Column(db.String(254), nullable=False, index=True)
    purpose = db.Column(db.String(16), nullable=False)
    code_mac = db.Column(db.String(64), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    sent = db.Column(db.Boolean, nullable=False, default=False)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    consumed = db.Column(db.Boolean, nullable=False, default=False)


class DeviceSession(db.Model):
    __tablename__ = 'identity_sessions'
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    member_id = db.Column(db.String(36), db.ForeignKey('members.id'), nullable=False, index=True)
    installation_id = db.Column(db.String(36), nullable=False)
    device_name = db.Column(db.String(80), nullable=False)
    access_hash = db.Column(db.String(64), nullable=False, unique=True)
    refresh_hash = db.Column(db.String(64), nullable=False, unique=True)
    access_expires_at = db.Column(db.DateTime, nullable=False)
    refresh_expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=now)
    revoked = db.Column(db.Boolean, nullable=False, default=False)
    rotation_id = db.Column(db.String(36), nullable=True)
    previous_hash = db.Column(db.String(64), nullable=True)
    rotation_receipt = db.Column(db.Text, nullable=True)
    receipt_expires_at = db.Column(db.DateTime, nullable=True)


class UsedRefresh(db.Model):
    __tablename__ = 'identity_used_refresh'
    token_hash = db.Column(db.String(64), primary_key=True)
    session_id = db.Column(db.String(36), db.ForeignKey('identity_sessions.id'), nullable=False, index=True)


class IdentityLimit(db.Model):
    __tablename__ = 'identity_limits'
    key = db.Column(db.String(64), primary_key=True)
    hits = db.Column(db.Integer, nullable=False)
    resets_at = db.Column(db.DateTime, nullable=False)
