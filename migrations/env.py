"""通过 Flask 应用配置执行在线或离线数据库迁移。"""

import logging
from logging.config import fileConfig

from alembic import context
from flask import current_app

config = context.config
fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')
target_db = current_app.extensions['migrate'].db


def get_metadata():
    return target_db.metadata


def get_engine_url():
    # 百分号须转义，避免配置解析器把密码中的字符作为插值表达式。
    return target_db.engine.url.render_as_string(hide_password=False).replace('%', '%%')


def run_migrations_offline():
    """只生成目标方言 SQL，不建立数据库连接。"""
    context.configure(url=get_engine_url().replace('%%', '%'), target_metadata=get_metadata(), literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """连接当前应用数据库并执行版本化迁移。"""
    def skip_empty_revision(migration_context, revision, directives):
        if getattr(config.cmd_opts, 'autogenerate', False) and directives[0].upgrade_ops.is_empty():
            directives[:] = []
            logger.info('数据库结构没有变化，无需新增迁移。')

    arguments = dict(current_app.extensions['migrate'].configure_args)
    arguments.setdefault('process_revision_directives', skip_empty_revision)
    with target_db.engine.connect() as connection:
        # SQLite 演示迁移需重建被引用表，关闭外键仅限当前迁移连接。
        sqlite = connection.dialect.name == 'sqlite'
        if sqlite:
            connection.exec_driver_sql('PRAGMA foreign_keys=OFF')
            connection.commit()
        context.configure(connection=connection, target_metadata=get_metadata(), **arguments)
        with context.begin_transaction():
            context.run_migrations()
        if sqlite:
            violations = connection.exec_driver_sql('PRAGMA foreign_key_check').fetchall()
            if violations:
                raise RuntimeError('迁移后发现外键异常，请保留备份并检查。')
            connection.exec_driver_sql('PRAGMA foreign_keys=ON')
            connection.commit()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
