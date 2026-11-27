"""浏览器验收只允许独立 MySQL _test 库，不使用正式/沙箱业务库。"""
import json
import os
from pathlib import Path

from flask_migrate import upgrade
from sqlalchemy.engine import make_url

from app.extensions import db


def database_url(name):
    value = os.environ.get(name, '')
    config = Path(__file__).resolve().parents[1] / 'tmp' / 'mysql-databases.json'
    if not value and config.exists():
        value = json.loads(config.read_text(encoding='utf-8-sig')).get(name, '')
    if not value:
        raise RuntimeError('请配置独立浏览器 MySQL 连接：' + name)
    url = make_url(value)
    if url.get_backend_name() != 'mysql' or not (url.database or '').endswith('_test'):
        raise RuntimeError('浏览器验收只允许名称以 _test 结尾的独立 MySQL 库。')
    return value


def prepare(application):
    with application.app_context():
        upgrade()
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()
