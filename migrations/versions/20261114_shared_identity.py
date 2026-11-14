"""Append shared CN identity; preserve all existing member and space identifiers."""
from alembic import op
import sqlalchemy as sa

revision = '20261114_shared_identity'
down_revision = '20261102_product_images'
branch_labels = None
depends_on = None


def upgrade():
    # 恢复库默认排序规则可能不同；外键沿用旧账号ID的实际类型与排序规则。
    member_key_type = next(column['type'] for column in sa.inspect(op.get_bind()).get_columns('members')
                           if column['name'] == 'id').copy()
    if op.get_bind().dialect.name == 'mysql':
        # 反射会省略继承自旧表的默认值，需读取列的有效字符规则。
        charset, collation = op.get_bind().execute(sa.text(
            "SELECT CHARACTER_SET_NAME, COLLATION_NAME FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='members' AND COLUMN_NAME='id'"
        )).one()
        if charset:
            member_key_type.charset = charset
            member_key_type.collation = collation
    op.add_column('members', sa.Column('auth_epoch', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('members', sa.Column('email_verified_at', sa.DateTime(), nullable=True))
    op.create_table('identity_challenges',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(254), nullable=False),
        sa.Column('purpose', sa.String(16), nullable=False),
        sa.Column('code_mac', sa.String(64), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('sent', sa.Boolean(), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('consumed', sa.Boolean(), nullable=False))
    op.create_index('ix_identity_challenges_email', 'identity_challenges', ['email'])
    op.create_table('identity_sessions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('member_id', member_key_type, sa.ForeignKey('members.id'), nullable=False),
        sa.Column('installation_id', sa.String(36), nullable=False),
        sa.Column('device_name', sa.String(80), nullable=False),
        sa.Column('access_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('refresh_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('access_expires_at', sa.DateTime(), nullable=False),
        sa.Column('refresh_expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('revoked', sa.Boolean(), nullable=False),
        sa.Column('rotation_id', sa.String(36)),
        sa.Column('previous_hash', sa.String(64)),
        sa.Column('rotation_receipt', sa.Text()),
        sa.Column('receipt_expires_at', sa.DateTime()))
    op.create_index('ix_identity_sessions_member_id', 'identity_sessions', ['member_id'])
    op.create_table('identity_used_refresh',
        sa.Column('token_hash', sa.String(64), primary_key=True),
        sa.Column('session_id', sa.String(36), sa.ForeignKey('identity_sessions.id'), nullable=False))
    op.create_index('ix_identity_used_refresh_session_id', 'identity_used_refresh', ['session_id'])
    op.create_table('identity_limits',
        sa.Column('key', sa.String(64), primary_key=True),
        sa.Column('hits', sa.Integer(), nullable=False),
        sa.Column('resets_at', sa.DateTime(), nullable=False))


def downgrade():
    raise RuntimeError('身份迁移不自动删除凭证或回退撤销状态。请按 shared-identity-runbook.md 恢复。')
