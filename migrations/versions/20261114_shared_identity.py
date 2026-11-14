"""Append shared CN identity; preserve all existing member and space identifiers."""
from alembic import op
import sqlalchemy as sa

revision = '20261114_shared_identity'
down_revision = '20261102_product_images'
branch_labels = None
depends_on = None


def upgrade():
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
        sa.Column('member_id', sa.String(36), sa.ForeignKey('members.id'), nullable=False),
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
