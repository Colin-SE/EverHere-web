"""浏览器验收：独立 MySQL，启动合成管理员和后台任务。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from app.extensions import db
from mysql_check_database import database_url, prepare

test_root = Path(__file__).resolve().parents[1] / 'test-results'
test_root.mkdir(exist_ok=True)
application = create_app({'SQLALCHEMY_DATABASE_URI': database_url('WORKFLOWS_DATABASE_URL'),
                          'SESSION_COOKIE_SECURE': False, 'TESTING': False})
prepare(application)
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
