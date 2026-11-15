"""Persist order processing, memoir jobs and public gallery images."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import LONGBLOB, VARCHAR

revision = '20261114_web_workflows'
down_revision = '20261114_shared_identity'
branch_labels = None
depends_on = None


def key_type(table):
    bind = op.get_bind()
    if bind.dialect.name == 'mysql':
        charset, collation = bind.execute(sa.text(
            "SELECT CHARACTER_SET_NAME, COLLATION_NAME FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=:table AND COLUMN_NAME='id'"
        ), {'table': table}).one()
        return VARCHAR(36, charset=charset, collation=collation)
    return sa.String(36)


def upgrade():
    op.add_column('photos', sa.Column('thumbnail_data', sa.LargeBinary(), nullable=True))
    with op.batch_alter_table('shop_orders') as batch:
        batch.add_column(sa.Column('processing_state', sa.String(24), nullable=False, server_default='pending'))
        batch.add_column(sa.Column('assignee_id', key_type('members'), nullable=True))
        batch.add_column(sa.Column('version', sa.Integer(), nullable=False, server_default='1'))
        batch.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True))
        batch.create_foreign_key('fk_shop_orders_assignee', 'members', ['assignee_id'], ['id'])
        batch.create_index('ix_shop_orders_assignee_id', ['assignee_id'])
        batch.create_index('ix_shop_order_processing_created', ['processing_state', 'created_at', 'id'])
    op.create_table(
        'shop_order_events',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('order_id', key_type('shop_orders'), sa.ForeignKey('shop_orders.id'), nullable=False),
        sa.Column('actor_id', sa.String(36), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(24), nullable=False),
        sa.Column('state', sa.String(24), nullable=False),
        sa.Column('message', sa.String(2000), nullable=False),
        sa.Column('visible', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('order_id', 'version'),
    )
    op.create_table(
        'memoir_jobs',
        sa.Column('revision_id', key_type('memoir_revisions'), sa.ForeignKey('memoir_revisions.id'), primary_key=True),
        sa.Column('state', sa.String(12), nullable=False, index=True),
        sa.Column('attempt', sa.Integer(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_table(
        'product_gallery_images',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('product_id', key_type('products'), sa.ForeignKey('products.id'), nullable=False, index=True),
        sa.Column('content_type', sa.String(40), nullable=False),
        sa.Column('data', sa.LargeBinary().with_variant(LONGBLOB(), 'mysql'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )


def downgrade():
    raise RuntimeError('回退代码前应保留订单处理、制作任务与商品图库数据。')
