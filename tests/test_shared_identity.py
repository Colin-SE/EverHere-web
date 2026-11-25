"""合成资料验证两端共用身份、旧账户兼容、撤销和失败恢复。"""
from datetime import timedelta
import os
from uuid import uuid4

import pytest
from flask_migrate import upgrade
from sqlalchemy import select
from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import LocalSpace, LifeRecord, now
from app.models_workflow import Member, SpaceOwnership
from app.models_identity import EmailChallenge, DeviceSession
from conftest import Client

PASSWORD = 'shared-password-123'
HEADERS = {'X-Everhere-Region': 'cn'}


@pytest.fixture
def shared(app):
    sent = []
    app.config.update(SHARED_IDENTITY_ENABLED=True, IDENTITY_SECRET='ab' * 32,
                      IDENTITY_TEST_MAILER=lambda *args: sent.append(args))
    return app, sent


def mobile(app, route, data=None, token=None, method='POST', client=None):
    headers = {**HEADERS, **({'Authorization': 'Bearer ' + token} if token else {})}
    return (client or app.test_client()).open('/v1/auth/' + route, method=method, json=data, headers=headers)


def challenge(shared, purpose='register', email='shared@example.test'):
    app, sent = shared
    response = mobile(app, 'code', dict(email=email, purpose=purpose))
    assert response.status_code == 200, response.json
    return response.json['challengeId'], sent[-1][2]


def register_mobile(shared, email='shared@example.test'):
    cid, code = challenge(shared, email=email)
    response = mobile(shared[0], 'register', dict(challengeId=cid, code=code, password=PASSWORD, role='admin'))
    assert response.status_code == 201, response.json
    return response.json['userId']


def login_mobile(app, email='shared@example.test', password=PASSWORD, installation=None):
    installation = installation or str(uuid4())
    response = mobile(app, 'login', dict(email=email, password=password, installationId=installation, deviceName='测试手机'))
    assert response.status_code == 200, response.json
    return response.json, installation


def test_mobile_account_logs_into_web_without_guest_claim(shared):
    app, _ = shared
    web = Client(app)
    record = web.create().json['data']
    user_id = register_mobile(shared)
    result = web.call('POST', '/accounts/login', dict(email='shared@example.test', password=PASSWORD))
    assert result.json['data']['member']['id'] == user_id
    assert result.json['data']['member']['role'] == 'user'
    assert web.call('GET', '/records/' + record['id']).status_code == 404
    assert web.call('GET', '/admin/products').status_code == 403
    tokens, _ = login_mobile(app)
    assert tokens['userId'] == user_id
    assert mobile(app, 'me', token=tokens['accessToken'], method='GET').json['userId'] == user_id
    # 移动端不签发浏览器 Cookie、不创建访客空间。
    with app.app_context():
        before = db.session.query(LocalSpace).count()
    result = mobile(app, 'login', {})
    assert 'Set-Cookie' not in result.headers
    with app.app_context():
        assert db.session.query(LocalSpace).count() == before


def test_web_register_mobile_login_and_explicit_space(shared):
    app, sent = shared
    web = Client(app)
    record = web.create().json['data']
    response = web.call('POST', '/accounts/code', dict(email='web@example.test', purpose='register'))
    cid = response.json['data']['challengeId']
    payload = dict(email='web@example.test', password=PASSWORD, name='网页用户', challengeId=cid, code=sent[-1][2], claimCurrentSpace=True)
    assert web.call('POST', '/accounts/register', {**payload, 'code': 'bad'}).status_code == 400
    result = web.call('POST', '/accounts/register', payload)
    assert result.status_code == 201
    assert web.call('GET', '/records/' + record['id']).status_code == 200
    tokens, _ = login_mobile(app, email='web@example.test')
    assert tokens['userId'] == result.json['data']['member']['id']


def test_legacy_password_id_role_and_records_preserved(shared):
    app, _ = shared
    with app.app_context():
        member = Member(id=str(uuid4()), email='legacy@example.test', name='原用户', role='admin', password_hash=generate_password_hash('old-pass10'))
        space = LocalSpace()
        db.session.add_all([member, space]); db.session.flush()
        db.session.add(SpaceOwnership(space_id=space.id, member_id=member.id)); db.session.commit()
        original_id, original_hash = member.id, member.password_hash
        record = LifeRecord(id=str(uuid4()), user_id=space.id, title='旧记录', content='原正文', record_state='occurred')
        record.source_id = record.id
        db.session.add(record); db.session.commit()
        record_id = record.id
    tokens, _ = login_mobile(app, email='legacy@example.test', password='old-pass10')
    assert tokens['userId'] == original_id
    with app.app_context():
        member = db.session.get(Member, original_id)
        assert member.password_hash == original_hash and member.role == 'admin'
        assert db.session.get(LifeRecord, record_id).content == '原正文'
    web = Client(app)
    assert web.call('POST', '/accounts/login', dict(email='legacy@example.test', password='old-pass10')).status_code == 200
    assert web.call('GET', '/records/' + record_id).json['data']['content'] == '原正文'
    response = mobile(app, 'code', dict(email='legacy@example.test', purpose='register'))
    assert response.status_code == 200
    assert shared[1] == []
    assert mobile(app, 'register', dict(challengeId=response.json['challengeId'], code='00000000', password=PASSWORD)).status_code == 400
    with app.app_context():
        assert db.session.query(Member).count() == 1


def test_refresh_retry_rotation_replay_and_restart(shared):
    app, _ = shared
    register_mobile(shared)
    tokens, installation = login_mobile(app)
    operation = str(uuid4())
    payload = dict(refreshToken=tokens['refreshToken'], installationId=installation, operationId=operation)
    assert mobile(app, 'refresh', {**payload, 'installationId': str(uuid4())}).status_code == 401
    result = mobile(app, 'refresh', payload)
    assert result.status_code == 200
    fresh = result.json
    assert fresh['refreshToken'] != tokens['refreshToken']
    assert fresh['sessionId'] == tokens['sessionId']
    assert mobile(app, 'refresh', payload).json == fresh
    assert mobile(app, 'me', token=tokens['accessToken'], method='GET').status_code == 401
    # 新 HTTP 客户端无 Cookie，凭持久凭证仍可恢复。
    assert mobile(app, 'me', token=fresh['accessToken'], method='GET').status_code == 200
    assert mobile(app, 'refresh', {**payload, 'operationId': str(uuid4())}).json['error'] == 'session_revoked'
    assert mobile(app, 'me', token=fresh['accessToken'], method='GET').status_code == 401


def test_reset_revokes_old_mobile_and_legacy_browser_cookie(shared):
    app, _ = shared
    register_mobile(shared)
    web = Client(app)
    assert web.call('POST', '/accounts/login', dict(email='shared@example.test', password=PASSWORD)).status_code == 200
    # 模拟升级前不含 epoch 的旧 Cookie。
    with web.client.session_transaction() as cookie:
        cookie.pop('auth_epoch', None)
    tokens, installation = login_mobile(app)
    cid, code = challenge(shared, purpose='reset')
    assert mobile(app, 'reset-password', dict(challengeId=cid, code=code, password='replacement-password')).json == {'reset': True}
    assert mobile(app, 'me', token=tokens['accessToken'], method='GET').status_code == 401
    assert mobile(app, 'refresh', dict(refreshToken=tokens['refreshToken'], installationId=installation, operationId=str(uuid4()))).status_code == 401
    assert web.call('GET', '/memoirs').status_code == 401
    assert mobile(app, 'reset-password', dict(challengeId=cid, code=code, password=PASSWORD)).status_code == 400
    new, _ = login_mobile(app, password='replacement-password')
    assert new['userId'] == tokens['userId']


def test_challenge_attempt_expiry_binding_and_resend(shared):
    app, _ = shared
    cid, code = challenge(shared)
    for _ in range(5):
        assert mobile(app, 'register', dict(challengeId=cid, code='wrong', password=PASSWORD)).json['error'] == 'invalid_code'
    assert mobile(app, 'register', dict(challengeId=cid, code=code, password=PASSWORD)).status_code == 400
    cid2, code2 = challenge(shared)
    with app.app_context():
        row = db.session.get(EmailChallenge, cid2)
        row.expires_at = now() - timedelta(seconds=1); db.session.commit()
    assert mobile(app, 'register', dict(challengeId=cid2, code=code2, password=PASSWORD)).status_code == 400
    cid3, code3 = challenge(shared)
    assert mobile(app, 'code', dict(email='shared@example.test', purpose='register')).status_code == 429
    web = Client(app)
    assert web.call('POST', '/accounts/register', dict(email='other@example.test', name='测试', password=PASSWORD, challengeId=cid3, code=code3)).status_code == 400
    assert mobile(app, 'register', dict(challengeId=cid3, code=code3, password=PASSWORD)).status_code == 201


def test_registration_cooldown_does_not_block_password_recovery(shared):
    app, sent = shared
    register_mobile(shared)
    email = 'shared@example.test'
    web = Client(app)
    for _ in range(2):
        assert web.call('POST', '/accounts/code', dict(email=email, purpose='register')).status_code == 200
    assert mobile(app, 'code', dict(email=email, purpose='register')).status_code == 429
    assert len(sent) == 1

    cid, code = challenge(shared, purpose='reset', email=email)
    assert mobile(app, 'code', dict(email=email, purpose='register')).status_code == 429
    assert mobile(app, 'reset-password', dict(challengeId=cid, code=code, password='replacement-password')).status_code == 200
    fresh = mobile(app, 'code', dict(email='fresh@example.test', purpose='register'))
    assert fresh.status_code == 200 and sent[-1][0] == 'fresh@example.test'


def test_region_cookie_csrf_logout_and_other_session_isolation(shared):
    app, _ = shared
    user_id = register_mobile(shared)
    first, _ = login_mobile(app)
    second, _ = login_mobile(app)
    assert app.test_client().post('/v1/auth/login', json={}).json == {'error': 'region_mismatch'}
    assert app.test_client().post('/v1/auth/login', json={}, headers={'X-Everhere-Region': 'global'}).status_code == 400
    web = Client(app)
    web.call('POST', '/accounts/login', dict(email='shared@example.test', password=PASSWORD))
    assert mobile(app, 'me', method='GET', client=web.client).status_code == 401
    assert web.client.post('/api/v1/accounts/code', json={}).status_code == 403
    sessions = mobile(app, 'sessions', token=first['accessToken'], method='GET').json['sessions']
    assert len(sessions) == 2 and sum(s['current'] for s in sessions) == 1
    assert mobile(app, 'logout', {}, token=first['accessToken']).json == {'revoked': True}
    assert mobile(app, 'me', token=first['accessToken'], method='GET').status_code == 401
    assert mobile(app, 'me', token=second['accessToken'], method='GET').status_code == 200
    assert mobile(app, 'logout-all', {}, token=second['accessToken']).status_code == 200
    assert web.call('GET', '/memoirs').status_code == 401


def test_mail_failure_and_unknown_reset_do_not_create_account(shared):
    app, sent = shared
    app.config['IDENTITY_TEST_MAILER'] = None
    result = mobile(app, 'code', dict(email='new@example.test', purpose='register'))
    assert result.status_code == 503 and result.json == {'error': 'mail_unavailable'}
    with app.app_context():
        assert db.session.query(EmailChallenge).count() == 0
    result = mobile(app, 'code', dict(email='unknown@example.test', purpose='reset'))
    assert result.status_code == 200 and not sent
    with app.app_context():
        assert db.session.query(Member).count() == 0


def test_disabled_by_default_and_request_bounds(app):
    assert mobile(app, 'login', {}).status_code == 503
    app.config.update(SHARED_IDENTITY_ENABLED=True, IDENTITY_SECRET='ab' * 32)
    assert mobile(app, 'login', {'padding': 'x' * 17000}).status_code == 413


def test_credentials_survive_server_restart_and_expired_access_refreshes(tmp_path):
    sent = []
    config = dict(SQLALCHEMY_DATABASE_URI='sqlite:///' + str(tmp_path / 'identity.sqlite'),
                  SHARED_IDENTITY_ENABLED=True, IDENTITY_SECRET='ab' * 32,
                  IDENTITY_TEST_MAILER=lambda *args: sent.append(args))
    first_app = create_app(config)
    with first_app.app_context():
        db.create_all()
    register_mobile((first_app, sent))
    tokens, installation = login_mobile(first_app)
    with first_app.app_context():
        device = db.session.get(DeviceSession, tokens['sessionId'])
        device.access_expires_at = now() - timedelta(seconds=1)
        db.session.commit(); db.session.remove(); db.engine.dispose()
    second_app = create_app(config)
    assert mobile(second_app, 'me', method='GET', token=tokens['accessToken']).status_code == 401
    fresh = mobile(second_app, 'refresh', dict(refreshToken=tokens['refreshToken'], installationId=installation, operationId=str(uuid4())))
    assert fresh.status_code == 200
    assert fresh.json['userId'] == tokens['userId']
    assert mobile(second_app, 'me', method='GET', token=fresh.json['accessToken']).status_code == 200


def test_cannot_revoke_another_accounts_session(shared):
    app, _ = shared
    register_mobile(shared)
    first, _ = login_mobile(app)
    register_mobile(shared, email='second@example.test')
    other, _ = login_mobile(app, email='second@example.test')
    assert mobile(app, 'revoke-session', dict(sessionId=other['sessionId']), token=first['accessToken']).status_code == 200
    assert mobile(app, 'me', method='GET', token=other['accessToken']).status_code == 200


def test_only_explicit_loopback_proxy_can_supply_forwarded_ip():
    from app.proxy import LoopbackProxy
    from werkzeug.test import Client as WsgiClient
    from werkzeug.wrappers import Response
    def target(environ, start_response):
        return Response(environ['REMOTE_ADDR'] + ' ' + environ['wsgi.url_scheme'])(environ, start_response)
    client = WsgiClient(LoopbackProxy(target), Response)
    headers = {'X-Forwarded-For': '203.0.113.4', 'X-Forwarded-Proto': 'https'}
    assert client.get('/', headers=headers, environ_overrides={'REMOTE_ADDR': '127.0.0.1'}).text == '203.0.113.4 https'
    assert client.get('/', headers=headers, environ_overrides={'REMOTE_ADDR': '198.51.100.2'}).text == '198.51.100.2 http'


@pytest.mark.parametrize('engine', ['sqlite', 'mysql'])
def test_additive_migration_keeps_old_member_and_space(tmp_path, engine):
    uri = 'sqlite:///' + str(tmp_path / 'migration.sqlite')
    if engine == 'mysql':
        uri = os.environ.get('IDENTITY_MIGRATION_TEST_URL')
        if not uri:
            pytest.skip('Requires an empty isolated MySQL migration _test database')
        from sqlalchemy.engine import make_url
        assert (make_url(uri).database or '').endswith('_test')
    application = create_app({'SQLALCHEMY_DATABASE_URI': uri})
    with application.app_context():
        upgrade(revision='20261102_product_images')
        if engine == 'mysql':
            # 重现恢复后库默认规则变化，但已有账号字段规则保持的情形。
            from sqlalchemy import text
            database = db.engine.url.database
            assert database.endswith('_test') and database.replace('_', '').isalnum()
            db.session.execute(text(f'ALTER DATABASE `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci'))
            db.session.commit()
        member_id, space_id = str(uuid4()), str(uuid4())
        # 迁移前使用原始 SQL，不让新模型依赖提前存在的列。
        from sqlalchemy import text
        encoded = generate_password_hash('old-pass10')
        db.session.execute(text('INSERT INTO members(id,email,name,password_hash,role,created_at) VALUES(:id,:email,:name,:hash,:role,:at)'), dict(id=member_id, email='before@example.test', name='旧用户', hash=encoded, role='user', at=now()))
        db.session.execute(text('INSERT INTO local_spaces(id,created_at,access_version) VALUES(:id,:at,:version)'), dict(id=space_id, at=now(), version=str(uuid4())))
        db.session.execute(text('INSERT INTO space_ownerships(space_id,member_id) VALUES(:space,:member)'), dict(space=space_id, member=member_id))
        record = LifeRecord(user_id=space_id, title='迁移前记录', content='保留的正文', record_state='occurred')
        db.session.add(record); db.session.flush()
        record_id = record.id
        db.session.commit()
        upgrade()
        member = db.session.get(Member, member_id)
        assert member.password_hash == encoded and member.auth_epoch == 0
        assert db.session.get(SpaceOwnership, space_id).member_id == member_id
        assert db.session.get(LifeRecord, record_id).content == '保留的正文'
        from alembic.autogenerate import compare_metadata
        from alembic.migration import MigrationContext
        assert compare_metadata(MigrationContext.configure(db.session.connection()), db.metadata) == []
