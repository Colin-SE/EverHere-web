"""Add the account-scoped album sync journal and original metadata."""
from alembic import op
import sqlalchemy as sa

revision = '20261125_album_sync'
down_revision = '20261115_alipay_commerce'
branch_labels = None
depends_on = None


def key_type(table):
    bind = op.get_bind()
    column_type = next(column['type'] for column in sa.inspect(bind).get_columns(table) if column['name'] == 'id').copy()
    if bind.dialect.name == 'mysql':
        charset, collation = bind.execute(sa.text(
            'SELECT CHARACTER_SET_NAME, COLLATION_NAME FROM information_schema.COLUMNS '
            "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=:table AND COLUMN_NAME='id'"), {'table': table}).one()
        if charset:
            column_type.charset, column_type.collation = charset, collation
    return column_type


def upgrade():
    space_key, photo_key = key_type('local_spaces'), key_type('photos')
    op.create_table('album_sync_changes',
        sa.Column('sequence', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), primary_key=True, autoincrement=True),
        sa.Column('space_id', space_key, sa.ForeignKey('local_spaces.id'), nullable=False),
        sa.Column('kind', sa.String(8), nullable=False),
        sa.Column('subject_id', sa.String(100), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('document', sa.JSON(), nullable=False),
        sa.UniqueConstraint('space_id', 'kind', 'subject_id', 'version'))
    op.create_index('ix_album_sync_changes_space_id', 'album_sync_changes', ['space_id'])
    op.create_table('album_sync_receipts',
        sa.Column('space_id', space_key, sa.ForeignKey('local_spaces.id'), primary_key=True),
        sa.Column('operation_hash', sa.String(64), primary_key=True),
        sa.Column('request_hash', sa.String(64), nullable=False),
        sa.Column('response', sa.JSON(), nullable=False))
    op.create_table('album_sync_conflicts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('space_id', space_key, sa.ForeignKey('local_spaces.id'), nullable=False),
        sa.Column('operation_id', sa.String(256), nullable=False),
        sa.Column('base_version', sa.BigInteger(), nullable=False),
        sa.Column('remote_version', sa.Integer(), nullable=False),
        sa.Column('local_document', sa.JSON(), nullable=False),
        sa.Column('remote_document', sa.JSON(), nullable=False),
        sa.Column('resolved', sa.Boolean(), nullable=False))
    op.create_index('ix_album_sync_conflicts_space_id', 'album_sync_conflicts', ['space_id'])
    op.create_table('album_sync_assets',
        sa.Column('photo_id', photo_key, sa.ForeignKey('photos.id'), primary_key=True),
        sa.Column('spec', sa.JSON(), nullable=False),
        sa.Column('ready', sa.Boolean(), nullable=False))


def downgrade():
    raise RuntimeError('Disable ALBUM_SYNC_ENABLED without deleting sync history or original metadata.')
