"""浏览器验收只使用内存合成库，不创建数据库备份。"""
import sys
from pathlib import Path
from uuid import uuid4

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from app import create_app
from app.extensions import db

# 内存 SQLite 由 Flask-SQLAlchemy 使用共享连接；无需保存可遗留的测试库文件；验收服务单线程避免共享内存连接的事务交错。
directory = root / 'test-results'
directory.mkdir(exist_ok=True)
stage = directory / ('qa-stage-' + str(uuid4()))
application = create_app({'SQLALCHEMY_DATABASE_URI': 'sqlite://', 'SESSION_COOKIE_SECURE': False,
                          'CLOUD_REGION': 'global', 'ARCHIVE_STAGE_DIRECTORY': str(stage)})
with application.app_context():
    db.create_all()
try:
    application.run(host='127.0.0.1', port=5003, debug=False, use_reloader=False, threaded=False)
finally:
    with application.app_context():
        db.session.remove()
        db.engine.dispose()
    # 仅清本进程的归档暂存文件，不递归删除目录。
    if stage.exists():
        assert stage.resolve().parent == directory.resolve()
        for item in stage.iterdir():
            assert item.is_file() and item.suffix == '.bin'
            item.unlink()
        stage.rmdir()
