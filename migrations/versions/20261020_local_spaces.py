"""将资料所有者迁移为独立本机空间，保留原始 ID 及内容。"""
from alembic import op
import sqlalchemy as sa

revision = '20261020_local_spaces'
down_revision = 'ef40b3df87a0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('local_spaces', sa.Column('id', sa.String(36), primary_key=True), sa.Column('created_at', sa.DateTime(), nullable=False), sa.Column('access_version', sa.String(36), nullable=False))
    op.execute('INSERT INTO local_spaces (id, created_at, access_version) SELECT id, created_at, auth_version FROM users')
    with op.batch_alter_table('users') as batch:
        batch.add_column(sa.Column('space_id', sa.String(36), nullable=True))
    op.execute('UPDATE users SET space_id = id')
    with op.batch_alter_table('users') as batch:
        batch.alter_column('space_id', existing_type=sa.String(36), nullable=False)
        batch.create_foreign_key('fk_users_space_id_local_spaces', 'local_spaces', ['space_id'], ['id'])
    for table in ('life_nodes', 'life_records', 'photos'):
        with op.batch_alter_table(table) as batch:
            batch.drop_constraint(f'fk_{table}_user_id_users', type_='foreignkey')
            batch.create_foreign_key(f'fk_{table}_user_id_local_spaces', 'local_spaces', ['user_id'], ['id'], ondelete='CASCADE')
    with op.batch_alter_table('life_records') as batch:
        batch.add_column(sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.false()))
    with op.batch_alter_table('life_records') as batch:
        batch.alter_column('is_deleted', existing_type=sa.Boolean(), server_default=None)
    op.create_table('cloud_connections',
        sa.Column('id', sa.String(36), sa.ForeignKey('local_spaces.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('account_id', sa.String(36), nullable=False), sa.Column('email', sa.String(254), nullable=False),
        sa.Column('token', sa.Text(), nullable=False), sa.Column('region', sa.String(8), nullable=False), sa.Column('device_id', sa.String(36), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False))



def downgrade():
    # 本机空间可独立创建且不可无损还原为账户，禁止自动破坏性降级。
    raise RuntimeError('此迁移不可自动降级，请使用升级前备份恢复。')
