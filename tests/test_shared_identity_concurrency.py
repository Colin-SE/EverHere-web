"""仅独立 MySQL 测试库执行锁并发；SQLite 不作为并发证据。"""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.extensions import db
from app.models_identity import EmailChallenge
from app.services import identity
from test_shared_identity import shared, challenge, register_mobile, login_mobile, mobile, PASSWORD


@pytest.fixture
def mysql_shared(shared):
    with shared[0].app_context():
        if db.engine.dialect.name != 'mysql':
            pytest.skip('Requires isolated MySQL _test database')
    return shared


def test_concurrent_refresh_same_operation_returns_same_tokens(mysql_shared):
    app, _ = mysql_shared
    register_mobile(mysql_shared)
    tokens, installation = login_mobile(app)
    payload = dict(refreshToken=tokens['refreshToken'], installationId=installation, operationId=str(uuid4()))
    barrier = Barrier(2)
    def rotate():
        barrier.wait(timeout=10)
        response = mobile(app, 'refresh', payload)
        return response.status_code, response.json
    with ThreadPoolExecutor(2) as pool:
        futures = [pool.submit(rotate) for _ in range(2)]
        results = [f.result(timeout=20) for f in futures]
    assert results[0][0] == results[1][0] == 200
    assert results[0][1] == results[1][1]


def test_concurrent_registration_consumes_once(mysql_shared):
    app, _ = mysql_shared
    cid, code = challenge(mysql_shared)
    barrier = Barrier(2)
    def create():
        barrier.wait(timeout=10)
        return mobile(app, 'register', dict(challengeId=cid, code=code, password=PASSWORD)).status_code
    with ThreadPoolExecutor(2) as pool:
        futures = [pool.submit(create) for _ in range(2)]
        assert sorted(f.result(timeout=20) for f in futures) == [201, 400]


def test_concurrent_resends_leave_only_last_challenge_valid(mysql_shared):
    app, sent = mysql_shared
    barrier = Barrier(2)
    def send():
        barrier.wait(timeout=10)
        return mobile(app, 'code', dict(email='parallel@example.test', purpose='register')).status_code
    with ThreadPoolExecutor(2) as pool:
        futures = [pool.submit(send) for _ in range(2)]
        assert [f.result(timeout=20) for f in futures] == [200, 200]
    with app.app_context():
        rows = db.session.scalars(select(EmailChallenge).where(EmailChallenge.email == 'parallel@example.test')).all()
        assert len(rows) == 2
        active = [r for r in rows if not r.consumed]
        assert len(active) == 1
        assert active[0].code_mac == identity.mac('code', active[0].id, active[0].email, 'register', sent[-1][2])


def test_password_reset_during_login_hash_check_rejects_old_password(mysql_shared, monkeypatch):
    app, _ = mysql_shared
    register_mobile(mysql_shared)
    cid, code = challenge(mysql_shared, purpose='reset')
    entered, proceed = Event(), Event()
    original = identity.check_password_hash
    def delayed(encoded, password):
        result = original(encoded, password)
        entered.set()
        assert proceed.wait(15)
        return result
    monkeypatch.setattr(identity, 'check_password_hash', delayed)
    def login():
        return mobile(app, 'login', dict(email='shared@example.test', password=PASSWORD, installationId=str(uuid4()), deviceName='race'))
    with ThreadPoolExecutor(1) as pool:
        pending = pool.submit(login)
        try:
            assert entered.wait(10)
            assert mobile(app, 'reset-password', dict(challengeId=cid, code=code, password='new-password-after-reset')).status_code == 200
        finally:
            proceed.set()
        assert pending.result(timeout=20).status_code == 401
