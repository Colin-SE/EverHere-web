"""沙箱必须隔离 MySQL，公开页面不再被额外 Basic Auth 拦截。"""
import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def sandbox(monkeypatch, tmp_path):
    path = Path(__file__).resolve().parents[1] / 'tools' / 'alipay-sandbox-server.py'
    spec = importlib.util.spec_from_file_location('sandbox_setup', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, 'STATE', tmp_path)
    monkeypatch.delenv('ALIPAY_SANDBOX_DATABASE_URL', raising=False)
    return module


@pytest.mark.parametrize('uri', [
    '', 'sqlite://', 'sqlite:///sandbox.sqlite3',
    'mysql+pymysql://user:never-print-this@localhost/life_album',
    'mysql+pymysql://user:never-print-this@localhost/lifealbumweb',
    'postgresql://user:never-print-this@localhost/life_album_sandbox',
])
def test_sandbox_rejects_shared_or_non_mysql_database(sandbox, monkeypatch, uri):
    monkeypatch.setenv('ALIPAY_SANDBOX_DATABASE_URL', uri)
    with pytest.raises(RuntimeError) as result:
        sandbox.database_url()
    assert 'never-print-this' not in str(result.value)


def test_sandbox_reads_its_own_mysql_config(sandbox):
    uri = 'mysql+pymysql://sandbox:synthetic@127.0.0.1/life_album_alipay_sandbox'
    (sandbox.STATE / 'database.json').write_text(json.dumps({'databaseUrl': uri}))
    assert sandbox.database_url() == uri


def test_prepare_removes_old_entry_password_without_changing_site_login(sandbox):
    path = sandbox.STATE / 'test-access.json'
    existing = {'entranceUser': 'old', 'entrancePassword': 'obsolete',
                'adminEmail': sandbox.ADMIN, 'adminPassword': 'site-password', 'sessionKey': 'session-key'}
    path.write_text(json.dumps(existing))
    sandbox.prepare()
    saved = json.loads(path.read_text())
    assert 'entranceUser' not in saved and 'entrancePassword' not in saved
    assert saved['adminPassword'] == 'site-password' and saved['sessionKey'] == 'session-key'


def test_sandbox_serves_site_directly_and_keeps_admin_permissions(sandbox, app, monkeypatch):
    sandbox.prepare()
    monkeypatch.setattr(sandbox, 'database_url', lambda: app.config['SQLALCHEMY_DATABASE_URI'])
    monkeypatch.setattr(sandbox, 'payment_config', lambda: {})
    monkeypatch.setattr(sandbox, 'create_app', lambda config: app)
    monkeypatch.setattr(sandbox, 'seed', lambda *args: None)
    monkeypatch.setattr(sandbox.sys, 'argv', ['alipay-sandbox-server.py'])
    captured = []
    monkeypatch.setattr(sandbox, 'serve', lambda application, **options: captured.append(application))
    sandbox.main()
    assert captured == [app]
    client = captured[0].test_client()
    response = client.get('/shop')
    assert response.status_code == 200 and 'WWW-Authenticate' not in response.headers
    assert client.get('/api/v1/admin/products').status_code == 401
