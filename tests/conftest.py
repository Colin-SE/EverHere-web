"""测试仅使用内存库或名称以 _test 结尾的专用库；不创建历史资料备份。"""
import os
from pathlib import Path
from uuid import uuid4

import pytest
from flask_migrate import upgrade
from sqlalchemy.engine import make_url

from app import create_app
from app.extensions import db


@pytest.fixture
def app():
    uri = os.environ.get('TEST_DATABASE_URL', 'sqlite://')
    if not uri.startswith('sqlite:') and not (make_url(uri).database or '').endswith('_test'):
        raise RuntimeError('TEST_DATABASE_URL 只能连接名称以 _test 结尾的专用库。')
    stage = Path.cwd() / 'test-results' / ('stage-' + str(uuid4()))
    application = create_app({'SQLALCHEMY_DATABASE_URI': uri, 'SESSION_COOKIE_SECURE': False, 'ARCHIVE_STAGE_DIRECTORY': str(stage)})
    with application.app_context():
        if uri.startswith('sqlite:'):
            db.create_all()
        else:
            upgrade()
        yield application
        db.session.remove()
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()
        db.engine.dispose()
    if stage.exists():
        assert stage.resolve().is_relative_to((Path.cwd() / 'test-results').resolve())
        for generated in stage.iterdir():
            assert generated.is_file() and generated.suffix == '.bin'
            generated.unlink()
        stage.rmdir()


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
