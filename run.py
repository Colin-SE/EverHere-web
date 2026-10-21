"""VS Code 本地运行入口：真实 MySQL、显式迁移、保留断点调试。"""

import os
from pathlib import Path

from dotenv import load_dotenv
from flask_migrate import upgrade
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from scripts.setup_mysql import SetupError, interactive_setup

ROOT = Path(__file__).resolve().parent


def prepare_application():
    """首次交互配置数据库；已有配置时只检查连接并应用迁移。"""
    os.chdir(ROOT)
    # 此入口明确使用 MySQL，不切换至示例数据。
    os.environ["APP_MODE"] = "mysql"
    env_path = ROOT / ".env"
    if not env_path.exists() and not os.environ.get("DATABASE_URL"):
        interactive_setup(env_path)
    load_dotenv(env_path, override=False)
    secret = os.environ.get("SECRET_KEY", "")
    if len(secret) < 32 or secret.startswith("replace-"):
        raise SetupError("请在 .env 设置有效的随机 SECRET_KEY；可用 Python secrets.token_hex(32) 生成。")
    from app import create_app
    from app.extensions import db

    application = create_app()
    with application.app_context():
        if db.engine.dialect.name != "mysql":
            raise SetupError("此运行入口要求真实 MySQL，请检查 .env 的 DATABASE_URL。")
        try:
            db.session.execute(text("SELECT 1"))
            db.session.rollback()
        except SQLAlchemyError:
            raise SetupError("无法连接 .env 中的 MySQL，请检查服务状态、账号密码、数据库名称和端口。") from None
        print("MySQL 连接成功，正在执行项目数据库迁移…", flush=True)
        try:
            upgrade(directory=str(ROOT / "migrations"))
        except Exception:
            raise SetupError("数据库迁移未完成，请检查上方的迁移日志和项目账号权限。") from None
    return application


def main():
    try:
        application = prepare_application()
        try:
            port = int(os.getenv("WEB_PORT", "5000"))
            if not 1 <= port <= 65535:
                raise ValueError
        except ValueError:
            raise SetupError("WEB_PORT 须为 1—65535 之间的端口号。") from None
        print(f"\n人生相册已准备就绪（MySQL）。打开 http://127.0.0.1:{port}/", flush=True)
        print("无需注册即可开始本机记录；云账号登录不会上传人生资料。停止运行请按 Ctrl+C 或 VS Code 的停止按钮。\n", flush=True)
        # 由 VS Code 提供调试器，关闭重载子进程，避免重复提示密码。
        application.run(host="127.0.0.1", port=port, debug=True, use_debugger=False, use_reloader=False)
    except (SetupError, EOFError, KeyboardInterrupt) as error:
        print(f"\n未启动：{error if isinstance(error, SetupError) else '已取消操作。'}", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
