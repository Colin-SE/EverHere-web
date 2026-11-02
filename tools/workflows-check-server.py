"""F1—F4 浏览器验收：独立内存库，仅启动时建立合成管理员，不读取 .env 数据库。"""
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from app.extensions import db

test_root = Path(__file__).resolve().parents[1] / 'test-results'
stage = test_root / ('workflows-stage-' + uuid4().hex)
application = create_app({'SQLALCHEMY_DATABASE_URI': 'sqlite://', 'SESSION_COOKIE_SECURE': False, 'CLOUD_REGION': 'global',
                          'ARCHIVE_STAGE_DIRECTORY': str(stage)})
with application.app_context():
    db.create_all()
result = application.test_cli_runner().invoke(args=['create-admin', '--email', 'reviewer@example.test', '--name', '合成管理员', '--password', 'browser-test-only-password'])
if result.exit_code:
    raise RuntimeError('无法建立合成验收管理员。')
try:
    application.run(host='127.0.0.1', port=5004, debug=False, threaded=False, use_reloader=False)
finally:
    with application.app_context():
        db.session.remove()
        db.engine.dispose()
    if stage.exists():
        assert stage.resolve().parent == test_root.resolve()
        for item in stage.iterdir():
            assert item.is_file() and item.suffix == '.bin'
            item.unlink()
        stage.rmdir()
