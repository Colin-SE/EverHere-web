"""Versioned album changes, retry receipts and pending originals."""
from .extensions import db
from .models import new_id


class AlbumChange(db.Model):
    __tablename__ = 'album_sync_changes'
    __table_args__ = (db.UniqueConstraint('space_id', 'kind', 'subject_id', 'version'),)
    sequence = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    space_id = db.Column(db.String(36), db.ForeignKey('local_spaces.id'), nullable=False, index=True)
    kind = db.Column(db.String(8), nullable=False)
    subject_id = db.Column(db.String(100), nullable=False)
    version = db.Column(db.Integer, nullable=False)
    document = db.Column(db.JSON, nullable=False)


class AlbumReceipt(db.Model):
    __tablename__ = 'album_sync_receipts'
    space_id = db.Column(db.String(36), db.ForeignKey('local_spaces.id'), primary_key=True)
    operation_hash = db.Column(db.String(64), primary_key=True)
    request_hash = db.Column(db.String(64), nullable=False)
    response = db.Column(db.JSON, nullable=False)


class AlbumConflict(db.Model):
    __tablename__ = 'album_sync_conflicts'
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    space_id = db.Column(db.String(36), db.ForeignKey('local_spaces.id'), nullable=False, index=True)
    operation_id = db.Column(db.String(256), nullable=False)
    base_version = db.Column(db.BigInteger, nullable=False)
    remote_version = db.Column(db.Integer, nullable=False)
    local_document = db.Column(db.JSON, nullable=False)
    remote_document = db.Column(db.JSON, nullable=False)
    resolved = db.Column(db.Boolean, nullable=False, default=False)


class AlbumAsset(db.Model):
    __tablename__ = 'album_sync_assets'
    photo_id = db.Column(db.String(36), db.ForeignKey('photos.id'), primary_key=True)
    spec = db.Column(db.JSON, nullable=False)
    ready = db.Column(db.Boolean, nullable=False, default=False)
