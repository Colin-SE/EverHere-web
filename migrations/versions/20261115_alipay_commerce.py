"""Append Alipay transaction, inventory and fulfillment data."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import VARCHAR

revision = '20261115_alipay_commerce'
down_revision = '20261114_web_workflows'
branch_labels = None
depends_on = None


def order_key():
    bind = op.get_bind()
    if bind.dialect.name == 'mysql':
        cset, coll = bind.execute(sa.text(
            "SELECT CHARACTER_SET_NAME, COLLATION_NAME FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='shop_orders' AND COLUMN_NAME='id'"
        )).one()
        return VARCHAR(36, charset=cset, collation=coll)
    return sa.String(36)


def upgrade():
    op.add_column('product_variants', sa.Column('stock_available', sa.Integer(), nullable=True))
    op.create_table(
        'shop_order_trades',
        sa.Column('order_id', order_key(), sa.ForeignKey('shop_orders.id'), primary_key=True),
        sa.Column('merchant_no', sa.String(32), nullable=False, unique=True),
        sa.Column('app_id', sa.String(32), nullable=False),
        sa.Column('seller_id', sa.String(32), nullable=False),
        sa.Column('environment', sa.String(12), nullable=False),
        sa.Column('amount_cents', sa.Integer(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('provider_no', sa.String(64), nullable=True, unique=True),
        sa.Column('paid_at', sa.DateTime()),
        sa.Column('address', sa.JSON()),
        sa.Column('fulfillment', sa.String(20), nullable=False),
        sa.Column('carrier', sa.String(80)),
        sa.Column('tracking', sa.String(100)),
        sa.Column('stock', sa.JSON(), nullable=False),
        sa.Column('stock_released', sa.Boolean(), nullable=False),
        sa.Column('refund_no', sa.String(32), nullable=True, unique=True),
        sa.Column('refund_state', sa.String(20)),
        sa.Column('refund_reason', sa.String(400)),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_shop_order_trades_expires_at', 'shop_order_trades', ['expires_at'])
    op.create_table(
        'shop_trade_events',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('order_id', order_key(), sa.ForeignKey('shop_orders.id'), nullable=False),
        sa.Column('event_key', sa.String(90), nullable=False),
        sa.Column('kind', sa.String(24), nullable=False),
        sa.Column('actor_id', sa.String(36)),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('order_id', 'event_key'),
    )


def downgrade():
    raise RuntimeError('回退须保留交易流水、退款记录和已确认的履约信息。')
