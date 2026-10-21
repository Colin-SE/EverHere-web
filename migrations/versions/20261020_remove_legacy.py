"""删除已停用的旧版账户与保险箱结构；不制作或保留备份。"""
from alembic import op
import sqlalchemy as sa

revision = '20261020_remove_legacy'
down_revision = '20261020_android_parity'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    if connection.execute(sa.text('SELECT COUNT(*) FROM users')).scalar():
        raise RuntimeError('旧账户尚未按用户要求清理，停止升级，禁止静默保留。')
    if connection.execute(sa.text('SELECT COUNT(*) FROM life_records WHERE is_private = true')).scalar():
        raise RuntimeError('旧保险箱资料尚未清理，停止升级。')
    op.drop_table('users')
    with op.batch_alter_table('life_records') as batch:
        batch.add_column(sa.Column('privacy', sa.String(16), nullable=False, server_default='standard'))
    with op.batch_alter_table('life_records') as batch:
        batch.alter_column('privacy', existing_type=sa.String(16), server_default=None)
        batch.drop_column('is_private')


def downgrade():
    raise RuntimeError('旧账户和历史资料已按用户要求删除，不提供恢复或备份。')
