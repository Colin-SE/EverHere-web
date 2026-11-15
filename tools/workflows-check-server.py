"""浏览器验收：使用一次性 SQLite，启动合成管理员和后台任务。"""
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from app.extensions import db

test_root = Path(__file__).resolve().parents[1] / 'test-results'
test_root.mkdir(exist_ok=True)
with TemporaryDirectory(dir=test_root) as folder:
    path = Path(folder) / 'browser.sqlite3'
    application = create_app({'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + path.as_posix(),
                              'SESSION_COOKIE_SECURE': False, 'TESTING': False})
    with application.app_context():
        db.create_all()
    result = application.test_cli_runner().invoke(args=[
        'create-admin', '--email', 'reviewer@example.test', '--name', '合成管理员',
        '--password', 'browser-test-only-password',
    ])
    if result.exit_code:
        raise RuntimeError('无法建立合成验收管理员。')
    try:
        application.run(host='127.0.0.1', port=5004, debug=False, threaded=True, use_reloader=False)
    finally:
        with application.app_context():
            db.session.remove()
            db.engine.dispose()
