"""F1—F4 新业务模型；通过独立账户映射保留已有空间、记录和照片 ID。"""
from flask_login import UserMixin
from sqlalchemy.dialects.mysql import LONGBLOB

from .extensions import db
from .models import new_id, now


class Member(UserMixin, db.Model):
    __tablename__ = 'members'
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    email = db.Column(db.String(254), nullable=False, unique=True)
    name = db.Column(db.String(80), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(16), nullable=False, default='user')
    created_at = db.Column(db.DateTime, nullable=False, default=now)


class SpaceOwnership(db.Model):
    __tablename__ = 'space_ownerships'
    space_id = db.Column(db.String(36), db.ForeignKey('local_spaces.id'), primary_key=True)
    member_id = db.Column(db.String(36), db.ForeignKey('members.id'), nullable=False, index=True)


class Memoir(db.Model):
    __tablename__ = 'memoirs'
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    owner_id = db.Column(db.String(36), db.ForeignKey('members.id'), nullable=False, index=True)
    space_id = db.Column(db.String(36), db.ForeignKey('local_spaces.id'), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    theme = db.Column(db.String(300), nullable=False, default='')
    draft = db.Column(db.JSON, nullable=False, default=list)
    state = db.Column(db.String(16), nullable=False, default='draft')
    version = db.Column(db.Integer, nullable=False, default=1)
    revision_number = db.Column(db.Integer, nullable=False, default=0)
    updated_at = db.Column(db.DateTime, nullable=False, default=now)


class MemoirRevision(db.Model):
    __tablename__ = 'memoir_revisions'
    __table_args__ = (db.UniqueConstraint('memoir_id', 'number'),)
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    memoir_id = db.Column(db.String(36), db.ForeignKey('memoirs.id'), nullable=False, index=True)
    number = db.Column(db.Integer, nullable=False)
    snapshot = db.Column(db.JSON, nullable=False)
    reviewer_id = db.Column(db.String(36), db.ForeignKey('members.id'), nullable=True)
    state = db.Column(db.String(16), nullable=False, default='submitted')
    reason = db.Column(db.String(2000), nullable=False, default='')
    render_error = db.Column(db.String(300), nullable=False, default='')
    layout = db.Column(db.JSON, nullable=False, default=dict)
    submitted_at = db.Column(db.DateTime, nullable=False, default=now)
    reviewed_at = db.Column(db.DateTime, nullable=True)


class MemoirAsset(db.Model):
    __tablename__ = 'memoir_assets'
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    revision_id = db.Column(db.String(36), db.ForeignKey('memoir_revisions.id'), nullable=False, index=True)
    kind = db.Column(db.String(16), nullable=False)
    content_type = db.Column(db.String(40), nullable=False)
    checksum = db.Column(db.String(64), nullable=False)
    data = db.Column(db.LargeBinary().with_variant(LONGBLOB(), 'mysql'), nullable=False)


class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(2000), nullable=False, default='')
    active = db.Column(db.Boolean, nullable=False, default=False)
    version = db.Column(db.Integer, nullable=False, default=1)


class ProductVariant(db.Model):
    __tablename__ = 'product_variants'
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    product_id = db.Column(db.String(36), db.ForeignKey('products.id'), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    kind = db.Column(db.String(24), nullable=False)
    price_cents = db.Column(db.Integer, nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    text_required = db.Column(db.Boolean, nullable=False, default=True)
    photo_required = db.Column(db.Boolean, nullable=False, default=False)
    version = db.Column(db.Integer, nullable=False, default=1)


class ShopOrder(db.Model):
    """F4 仅创建待支付订单；支付、取消与交付状态机在 F5 实施。"""
    __tablename__ = 'shop_orders'
    __table_args__ = (db.UniqueConstraint('buyer_id', 'request_key'),)
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    buyer_id = db.Column(db.String(36), db.ForeignKey('members.id'), nullable=False, index=True)
    request_key = db.Column(db.String(64), nullable=False)
    request_hash = db.Column(db.String(64), nullable=False)
    total_cents = db.Column(db.Integer, nullable=False)
    state = db.Column(db.String(20), nullable=False, default='unpaid')
    created_at = db.Column(db.DateTime, nullable=False, default=now)


class ShopOrderItem(db.Model):
    __tablename__ = 'shop_order_items'
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    order_id = db.Column(db.String(36), db.ForeignKey('shop_orders.id'), nullable=False, index=True)
    variant_id = db.Column(db.String(36), db.ForeignKey('product_variants.id'), nullable=False)
    revision_id = db.Column(db.String(36), db.ForeignKey('memoir_revisions.id'), nullable=True)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price_cents = db.Column(db.Integer, nullable=False)
    snapshot = db.Column(db.JSON, nullable=False)
    photo_type = db.Column(db.String(40), nullable=True)
    photo_data = db.Column(db.LargeBinary().with_variant(LONGBLOB(), 'mysql'), nullable=True)
