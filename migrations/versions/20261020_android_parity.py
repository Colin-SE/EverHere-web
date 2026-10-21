"""追加本机草稿、人物修订/墓碑与原图稳定 ID；不改已发布迁移。"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import LONGBLOB, MEDIUMBLOB

revision = '20261020_android_parity'
down_revision = '20261020_local_spaces'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('reminders',
        sa.Column('id', sa.String(36), primary_key=True), sa.Column('owner_id', sa.String(36), sa.ForeignKey('local_spaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_id', sa.String(100), nullable=False), sa.Column('payload', sa.JSON(), nullable=False), sa.UniqueConstraint('owner_id', 'source_id', name='uq_reminders_owner_id'))
    op.create_table('archive_jobs',
        sa.Column('id', sa.String(36), primary_key=True), sa.Column('owner_id', sa.String(36), sa.ForeignKey('local_spaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_hash', sa.String(64), nullable=False), sa.Column('target_hash', sa.String(64), nullable=False), sa.Column('summary', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False), sa.Column('committed_at', sa.DateTime(), nullable=True))
    op.create_index('ix_archive_jobs_owner_id', 'archive_jobs', ['owner_id'])
    op.create_table('drafts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('owner_id', sa.String(36), sa.ForeignKey('local_spaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('kind', sa.String(16), nullable=False), sa.Column('target_id', sa.String(100), nullable=False),
        sa.Column('base_version', sa.Integer(), nullable=False), sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False), sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('committed_at', sa.DateTime(), nullable=True))
    op.create_index('ix_drafts_owner_id', 'drafts', ['owner_id'])
    with op.batch_alter_table('life_nodes') as batch:
        batch.add_column(sa.Column('version', sa.Integer(), nullable=False, server_default='1'))
        batch.add_column(sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.false()))
    with op.batch_alter_table('life_nodes') as batch:
        batch.alter_column('version', existing_type=sa.Integer(), server_default=None)
        batch.alter_column('is_deleted', existing_type=sa.Boolean(), server_default=None)
    nodes = sa.table('life_nodes', sa.column('id', sa.String()), sa.column('payload', sa.JSON()), sa.column('is_deleted', sa.Boolean()))
    for row in op.get_bind().execute(sa.select(nodes.c.id, nodes.c.payload)):
        if row.payload.get('androidDocument', {}).get('deletedAt') is not None:
            op.get_bind().execute(nodes.update().where(nodes.c.id == row.id).values(is_deleted=True))
    with op.batch_alter_table('photos') as batch:
        if op.get_bind().dialect.name == 'mysql':
            batch.alter_column('data', existing_type=MEDIUMBLOB(), type_=LONGBLOB(), existing_nullable=False)
        batch.add_column(sa.Column('source_id', sa.String(100), nullable=True))
        batch.create_unique_constraint('uq_photos_user_id', ['user_id', 'source_id'])


def downgrade():
    raise RuntimeError('降级将丢失草稿与稳定资产 ID，请从升级前备份恢复。')
