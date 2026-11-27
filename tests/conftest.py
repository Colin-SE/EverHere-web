"""测试仅使用名称以 _test 结尾的独立 MySQL 库。"""
import os

import pytest
from flask_migrate import upgrade
from sqlalchemy import MetaData, create_engine
from sqlalchemy.engine import make_url

from app import create_app
from app.extensions import db


@pytest.fixture
def app():
    uri = os.environ.get('TEST_DATABASE_URL', '')
    if not uri or make_url(uri).get_backend_name() != 'mysql' or not (make_url(uri).database or '').endswith('_test'):
        raise RuntimeError('TEST_DATABASE_URL 只能连接名称以 _test 结尾的专用库。')
    application = create_app({'SQLALCHEMY_DATABASE_URI': uri, 'SESSION_COOKIE_SECURE': False})
    with application.app_context():
        upgrade()
    # 每个请求独立结束会话，模拟真实 Flask 生命周期；不得让 MySQL
    # REPEATABLE READ 快照跨越整条用例，遮蔽其他连接已经提交的资料。
    try:
        yield application
    finally:
        with application.app_context():
            db.session.remove()
            for table in reversed(db.metadata.sorted_tables):
                db.session.execute(table.delete())
            db.session.commit()
            db.engine.dispose()


@pytest.fixture
def migration_database_url():
    """迁移验收独占另一专用库；只重置明确的 _test 库。"""
    uri = os.environ.get('IDENTITY_MIGRATION_TEST_URL', '')
    if not uri:
        pytest.skip('Requires a separate MySQL migration _test database')
    url = make_url(uri)
    assert url.get_backend_name() == 'mysql' and (url.database or '').endswith('_test')
    assert url.database != make_url(os.environ['TEST_DATABASE_URL']).database
    engine = create_engine(uri)
    def clear_schema():
        metadata = MetaData()
        metadata.reflect(engine)
        metadata.drop_all(engine)
    clear_schema()
    try:
        yield uri
    finally:
        clear_schema()
        engine.dispose()



class Client:
    def __init__(self, app):
        self.client = app.test_client()
        self.token = self.client.get('/api/v1/auth/session').json['data']['csrfToken']

    def call(self, method, path, json=None, **kwargs):
        result = self.client.open('/api/v1' + path, method=method, json=json, headers={'X-CSRF-Token': self.token}, **kwargs)
        if result.is_json and result.json.get('data', {}).get('csrfToken'):
            self.token = result.json['data']['csrfToken']
        return result

    def create(self, **changes):
        return self.call('POST', '/records', {'title': '一段记忆', 'content': '正文', 'eventDate': '2026-10-16', **changes})


@pytest.fixture
def client(app):
    return Client(app)
