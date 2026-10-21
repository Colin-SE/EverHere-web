"""领域模型：一份人生记录通过关联表服务所有视图。"""

from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy.dialects.mysql import LONGBLOB, MEDIUMTEXT

from .extensions import db


def new_id():
    return str(uuid4())


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class LocalSpace(db.Model):
    """本机资料所有者，与本机档案密码、云账号生命周期无关。"""
    __tablename__ = "local_spaces"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    access_version = db.Column(db.String(36), nullable=False, default=new_id)
    created_at = db.Column(db.DateTime, nullable=False, default=now)


class CloudConnection(db.Model):
    """凭证只留在本机数据库，不放入浏览器 Cookie 或日志。"""
    __tablename__ = "cloud_connections"
    id = db.Column(db.String(36), db.ForeignKey("local_spaces.id", ondelete="CASCADE"), primary_key=True)
    account_id = db.Column(db.String(36), nullable=False)
    email = db.Column(db.String(254), nullable=False)
    token = db.Column(db.Text, nullable=False)
    region = db.Column(db.String(8), nullable=False)
    device_id = db.Column(db.String(36), nullable=False, default=new_id)
    enabled = db.Column(db.Boolean, nullable=False, default=False)


class LifeRecord(db.Model):
    __tablename__ = "life_records"
    __table_args__ = (db.UniqueConstraint("user_id", "source_id"), db.Index("ix_records_owner_date", "user_id", "event_date"))
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    # 历史列名 user_id 保留，实际外键为本机空间，不再归属登录账户。
    user_id = db.Column(db.String(36), db.ForeignKey("local_spaces.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id = db.Column(db.String(100), nullable=False, default=new_id)
    title = db.Column(db.String(200), nullable=False, default="")
    content = db.Column(db.Text().with_variant(MEDIUMTEXT(), "mysql"), nullable=False, default="")
    event_date = db.Column(db.Date, nullable=True)
    record_state = db.Column(db.String(16), nullable=False)
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    privacy = db.Column(db.String(16), nullable=False, default="standard")
    payload = db.Column(db.JSON, nullable=False, default=dict)
    version = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, nullable=False, default=now)
    updated_at = db.Column(db.DateTime, nullable=False, default=now)
    links = db.relationship("RecordNode", cascade="all, delete-orphan", passive_deletes=True)


class LifeNode(db.Model):
    """统一持久化对象、线索和阶段，各 kind 保持独立字段语义。"""
    __tablename__ = "life_nodes"
    __table_args__ = (db.UniqueConstraint("user_id", "kind", "source_id"),)
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    # 历史列名 user_id 保留，实际外键为本机空间，不再归属登录账户。
    user_id = db.Column(db.String(36), db.ForeignKey("local_spaces.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id = db.Column(db.String(100), nullable=False, default=new_id)
    kind = db.Column(db.String(16), nullable=False)
    version = db.Column(db.Integer, nullable=False, default=1)
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    name = db.Column(db.String(120), nullable=False)
    payload = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, nullable=False, default=now)
    updated_at = db.Column(db.DateTime, nullable=False, default=now)
    links = db.relationship("RecordNode", cascade="all, delete-orphan", passive_deletes=True)


class Reminder(db.Model):
    """仅保留安卓版既有提醒元信息，不在 Web 启动通知调度。"""
    __tablename__ = "reminders"
    __table_args__ = (db.UniqueConstraint("owner_id", "source_id"),)
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    owner_id = db.Column(db.String(36), db.ForeignKey("local_spaces.id", ondelete="CASCADE"), nullable=False)
    source_id = db.Column(db.String(100), nullable=False)
    payload = db.Column(db.JSON, nullable=False)


class ArchiveJob(db.Model):
    """只读预览与恢复回执；文件只在实例私有目录按随机 ID 暂存。"""
    __tablename__ = "archive_jobs"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    owner_id = db.Column(db.String(36), db.ForeignKey("local_spaces.id", ondelete="CASCADE"), nullable=False, index=True)
    source_hash = db.Column(db.String(64), nullable=False)
    target_hash = db.Column(db.String(64), nullable=False)
    summary = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=now)
    committed_at = db.Column(db.DateTime, nullable=True)


class Draft(db.Model):
    """端内草稿与提交回执：不计正式数量，不进入普通备份或云同步。"""
    __tablename__ = "drafts"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    owner_id = db.Column(db.String(36), db.ForeignKey("local_spaces.id", ondelete="CASCADE"), nullable=False, index=True)
    kind = db.Column(db.String(16), nullable=False)
    target_id = db.Column(db.String(100), nullable=False, default=new_id)
    base_version = db.Column(db.Integer, nullable=False, default=0)
    version = db.Column(db.Integer, nullable=False, default=1)
    payload = db.Column(db.JSON, nullable=False, default=dict)
    updated_at = db.Column(db.DateTime, nullable=False, default=now)
    committed_at = db.Column(db.DateTime, nullable=True)


class RecordNode(db.Model):
    __tablename__ = "record_nodes"
    record_id = db.Column(db.String(36), db.ForeignKey("life_records.id", ondelete="CASCADE"), primary_key=True)
    node_id = db.Column(db.String(36), db.ForeignKey("life_nodes.id", ondelete="CASCADE"), primary_key=True)
    node = db.relationship("LifeNode", overlaps="links")
    record = db.relationship("LifeRecord", overlaps="links")


class Photo(db.Model):
    """图片在数据库事务内管理，避免文件与账户删除不同步。"""
    __tablename__ = "photos"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    # 历史列名 user_id 保留，实际外键为本机空间，不再归属登录账户。
    user_id = db.Column(db.String(36), db.ForeignKey("local_spaces.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id = db.Column(db.String(100), nullable=True)
    __table_args__ = (db.UniqueConstraint("user_id", "source_id"),)
    content_type = db.Column(db.String(30), nullable=False)
    data = db.Column(db.LargeBinary().with_variant(LONGBLOB(), "mysql"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=now)
