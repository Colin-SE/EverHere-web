"""生产 WSGI 入口；数据库结构通过 flask db upgrade 管理。"""

from app import create_app

app = create_app()
