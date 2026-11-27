"""浏览器验收使用独立 MySQL 合成库。"""
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from app import create_app
from app.extensions import db
from mysql_check_database import database_url, prepare

directory = root / 'test-results'
directory.mkdir(exist_ok=True)
application = create_app({'SQLALCHEMY_DATABASE_URI': database_url('BROWSER_DATABASE_URL'), 'SESSION_COOKIE_SECURE': False})
prepare(application)
try:
    application.run(host='127.0.0.1', port=5003, debug=False, use_reloader=False, threaded=False)
finally:
    with application.app_context():
        db.session.remove()
        db.engine.dispose()
    # 仅清本进程的归档暂存文件，不递归删除目录。
