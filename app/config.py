"""正式运行连接 MySQL；SQLite 仅由测试配置显式注入。"""

import os
from datetime import timedelta

from dotenv import load_dotenv
from sqlalchemy.engine import URL

load_dotenv()


def settings():
    secret = os.getenv("SECRET_KEY")
    if not secret:
        raise RuntimeError("请在 .env 设置独立随机 SECRET_KEY。")
    if os.getenv("APP_ENV") == "production" and (len(secret) < 32 or secret.startswith("replace-")):
        raise RuntimeError("生产环境必须设置至少 32 位的独立随机 SECRET_KEY。")
    mysql_url = URL.create("mysql+pymysql", username="life_album", password=os.getenv("MYSQL_PASSWORD", "change-me"), host=os.getenv("MYSQL_HOST", "127.0.0.1"), port=3306, database="life_album", query={"charset": "utf8mb4"})
    return {
        "SECRET_KEY": secret,
        "SQLALCHEMY_DATABASE_URI": os.getenv("DATABASE_URL") or mysql_url,
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SQLALCHEMY_ENGINE_OPTIONS": {"pool_pre_ping": True},
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": os.getenv("SESSION_COOKIE_SECURE", "true" if os.getenv("APP_ENV") == "production" else "false").lower() == "true",
        "PERMANENT_SESSION_LIFETIME": timedelta(days=7),
        "MAX_CONTENT_LENGTH": 520 * 1024 * 1024,
        "RATELIMIT_STORAGE_URI": os.getenv("RATELIMIT_STORAGE_URI", "memory://"),
        "CLOUD_API_URL": os.getenv("CLOUD_API_URL", ""),
        "CLOUD_REGION": os.getenv("CLOUD_REGION", "cn"),
        "EVENT_TIMEZONE": os.getenv("EVENT_TIMEZONE", "Asia/Shanghai"),
    }
