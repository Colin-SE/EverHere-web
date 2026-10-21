"""${message}

迁移版本： ${up_revision}
上个版本： ${down_revision | comma,n}
创建时间： ${create_date}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# Alembic 使用的迁移版本标识。
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade():
    ${upgrades if upgrades else "pass"}


def downgrade():
    ${downgrades if downgrades else "pass"}
