"""初始化人生相册数据库结构。

版本：ef40b3df87a0
上个版本：无
创建日期：2026-10-17

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# Alembic 使用的迁移版本标识。
revision = 'ef40b3df87a0'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # 按外键依赖顺序建表，关联表最后创建。
    op.create_table('users',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('auth_version', sa.String(length=36), nullable=False),
    sa.Column('archive_extras', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
    sa.UniqueConstraint('email', name=op.f('uq_users_email'))
    )
    op.create_table('life_nodes',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('source_id', sa.String(length=100), nullable=False),
    sa.Column('kind', sa.String(length=16), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('payload', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_life_nodes_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_life_nodes')),
    sa.UniqueConstraint('user_id', 'kind', 'source_id', name=op.f('uq_life_nodes_user_id'))
    )
    with op.batch_alter_table('life_nodes', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_life_nodes_user_id'), ['user_id'], unique=False)

    op.create_table('life_records',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('source_id', sa.String(length=100), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('content', sa.Text().with_variant(mysql.MEDIUMTEXT(), 'mysql'), nullable=False),
    sa.Column('event_date', sa.Date(), nullable=True),
    sa.Column('record_state', sa.String(length=16), nullable=False),
    sa.Column('is_private', sa.Boolean(), nullable=False),
    sa.Column('payload', sa.JSON(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_life_records_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_life_records')),
    sa.UniqueConstraint('user_id', 'source_id', name=op.f('uq_life_records_user_id'))
    )
    with op.batch_alter_table('life_records', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_life_records_user_id'), ['user_id'], unique=False)
        batch_op.create_index('ix_records_owner_date', ['user_id', 'event_date'], unique=False)

    op.create_table('photos',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('content_type', sa.String(length=30), nullable=False),
    sa.Column('data', sa.LargeBinary().with_variant(mysql.MEDIUMBLOB(), 'mysql'), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_photos_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_photos'))
    )
    with op.batch_alter_table('photos', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_photos_user_id'), ['user_id'], unique=False)

    op.create_table('record_nodes',
    sa.Column('record_id', sa.String(length=36), nullable=False),
    sa.Column('node_id', sa.String(length=36), nullable=False),
    sa.ForeignKeyConstraint(['node_id'], ['life_nodes.id'], name=op.f('fk_record_nodes_node_id_life_nodes'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['record_id'], ['life_records.id'], name=op.f('fk_record_nodes_record_id_life_records'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('record_id', 'node_id', name=op.f('pk_record_nodes'))
    )


def downgrade():
    # 回退会删除业务表，仅用于明确授权的数据库结构回滚。
    op.drop_table('record_nodes')
    with op.batch_alter_table('photos', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_photos_user_id'))

    op.drop_table('photos')
    with op.batch_alter_table('life_records', schema=None) as batch_op:
        batch_op.drop_index('ix_records_owner_date')
        batch_op.drop_index(batch_op.f('ix_life_records_user_id'))

    op.drop_table('life_records')
    with op.batch_alter_table('life_nodes', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_life_nodes_user_id'))

    op.drop_table('life_nodes')
    op.drop_table('users')
