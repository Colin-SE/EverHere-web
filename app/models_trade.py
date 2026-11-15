"""P4 支付账本、订单地址快照与独立交付状态。"""
from .extensions import db
from .models import new_id, now


class OrderTrade(db.Model):
    __tablename__ = 'shop_order_trades'
    order_id = db.Column(db.String(36), db.ForeignKey('shop_orders.id'), primary_key=True)
    merchant_no = db.Column(db.String(32), nullable=False, unique=True)
    app_id = db.Column(db.String(32), nullable=False)
    seller_id = db.Column(db.String(32), nullable=False)
    environment = db.Column(db.String(12), nullable=False)
    amount_cents = db.Column(db.Integer, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    provider_no = db.Column(db.String(64), nullable=True, unique=True)
    paid_at = db.Column(db.DateTime, nullable=True)
    address = db.Column(db.JSON, nullable=True)
    fulfillment = db.Column(db.String(20), nullable=False, default='pending')
    carrier = db.Column(db.String(80), nullable=True)
    tracking = db.Column(db.String(100), nullable=True)
    stock = db.Column(db.JSON, nullable=False, default=dict)
    stock_released = db.Column(db.Boolean, nullable=False, default=False)
    refund_no = db.Column(db.String(32), nullable=True, unique=True)
    refund_state = db.Column(db.String(20), nullable=True)
    refund_reason = db.Column(db.String(400), nullable=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=now)


class TradeEvent(db.Model):
    __tablename__ = 'shop_trade_events'
    __table_args__ = (db.UniqueConstraint('order_id', 'event_key'),)
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    order_id = db.Column(db.String(36), db.ForeignKey('shop_orders.id'), nullable=False)
    event_key = db.Column(db.String(90), nullable=False)
    kind = db.Column(db.String(24), nullable=False)
    actor_id = db.Column(db.String(36), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=now)
