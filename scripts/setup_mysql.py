"""在本地终端输入管理员密码，创建项目独立的 MySQL 库与账号。"""

import getpass
import json
import re
import secrets
import sys
from pathlib import Path

import pymysql
from sqlalchemy.engine import URL

ROOT = Path(__file__).resolve().parents[1]


class SetupError(Exception):
    """可直接展示给开发者、且不含密码的初始化错误。"""


def validate_database_name(name):
    # 数据库名限制为字母数字，避免 SQL 标识符注入和授权通配符。
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9]{0,47}", name):
        raise SetupError("数据库名请使用字母开头的 1—48 位字母或数字。")
    if name.lower() in {"mysql", "sys", "information_schema", "performance_schema"}:
        raise SetupError("不能使用 MySQL 系统数据库。")
    return name


def write_environment(path, *, database, username, password, port):
    """只创建新配置，不覆盖开发者原有的 .env。"""
    url = URL.create("mysql+pymysql", username=username, password=password,
                     host="127.0.0.1", port=port, database=database,
                     query={"charset": "utf8mb4"})
    content = (
        "# 本机 MySQL 配置。仅保存项目专用账号，不保存管理员密码。\n"
        "APP_ENV=development\n"
        f"SECRET_KEY={secrets.token_hex(32)}\n"
        f"DATABASE_URL={json.dumps(url.render_as_string(hide_password=False))}\n"
        "SESSION_COOKIE_SECURE=false\n"
        "RATELIMIT_STORAGE_URI=memory://\n"
    )
    try:
        with path.open("x", encoding="utf-8") as file:
            file.write(content)
        if sys.platform != "win32":
            path.chmod(0o600)
    except FileExistsError:
        raise SetupError(".env 已存在，未覆盖。请检查现有连接配置。") from None


def provision(*, admin_user, admin_password, database, port=3306, env_path=None, connect=None):
    """仅在本机创建新库，既有数据库与账号均不修改。"""
    path = Path(env_path) if env_path else ROOT / ".env"
    if path.exists():
        raise SetupError(".env 已存在，未执行建库或修改账号。")
    validate_database_name(database)
    if not isinstance(port, int) or not 1 <= port <= 65535:
        raise SetupError("MySQL 端口须在 1—65535 之间。")
    connector = connect or pymysql.connect
    # 单独生成用户名和高强度密码，不重复使用管理员身份运行 Web 应用。
    username = "lifealbum_" + secrets.token_hex(4)
    password = secrets.token_urlsafe(32) + "Aa9!"
    connection = None
    try:
        connection = connector(host="127.0.0.1", port=port, user=admin_user,
                               password=admin_password, charset="utf8mb4", autocommit=True,
                               connect_timeout=5, read_timeout=15, write_timeout=15)
        with connection.cursor() as cursor:
            cursor.execute("SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = %s", (database,))
            if cursor.fetchone():
                raise SetupError("该数据库已存在，本向导不会修改它。请换一个新库名，或手动配置已有账号。")
            cursor.execute(f"CREATE DATABASE `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print(f"已创建本项目数据库：{database}")
            cursor.execute("CREATE USER %s@'localhost' IDENTIFIED BY %s", (username, password))
            cursor.execute(
                f"GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, DROP, REFERENCES ON `{database}`.* TO %s@'localhost'",
                (username,),
            )
        # 保存之前实际验证专用账号，不把管理员连接成功当作应用连接成功。
        application_connection = connector(host="127.0.0.1", port=port, user=username,
                                           password=password, database=database,
                                           charset="utf8mb4", connect_timeout=5)
        application_connection.close()
        write_environment(path, database=database, username=username, password=password, port=port)
        print("项目专用账号已验证，连接配置已写入本地 .env。")
        return path
    except pymysql.MySQLError as error:
        code = error.args[0] if error.args else "unknown"
        messages = {
            1045: "MySQL 用户名或密码不正确，请重新运行并输入正确的管理员密码。",
            1044: "当前管理员账号没有创建项目数据库的权限。",
            1142: "当前管理员账号缺少创建账号或授予权限所需的权限。",
            1227: "当前管理员账号没有创建账号或授权的权限。",
            2003: "无法连接本机 MySQL，请确认 MySQL80 服务已启动且端口正确。",
            1819: "MySQL 密码策略拒绝了项目密码，请检查服务端的密码策略配置。",
        }
        # 不打印驱动原异常，避免其中的 SQL 或认证参数进入终端日志。
        raise SetupError(messages.get(code, f"MySQL 初始化失败，错误代码：{code}。")) from None
    finally:
        if connection is not None:
            connection.close()


def interactive_setup(env_path=None):
    path = Path(env_path) if env_path else ROOT / ".env"
    if path.exists():
        print("检测到已有 .env，将使用现有连接，不重置数据库或密码。")
        return path
    print("\n首次配置：连接真实 MySQL，不创建演示账户或示例日记。")
    print("管理员密码只在当前终端隐藏输入，用于创建项目专用库和账号。\n")
    admin_user = input("MySQL 管理员用户名 [root]：").strip() or "root"
    port_input = input("本机 MySQL 端口 [3306]：").strip() or "3306"
    try:
        port = int(port_input)
    except ValueError:
        raise SetupError("端口必须为数字。") from None
    database = validate_database_name(input("新建项目数据库名 [lifealbumweb]：").strip() or "lifealbumweb")
    admin_password = getpass.getpass("MySQL 管理员密码（输入时不显示字符）：")
    try:
        return provision(admin_user=admin_user, admin_password=admin_password,
                         database=database, port=port, env_path=path)
    finally:
        admin_password = None


if __name__ == "__main__":
    try:
        interactive_setup()
    except (SetupError, EOFError, KeyboardInterrupt) as error:
        print(f"\n初始化未完成：{error if isinstance(error, SetupError) else '已取消输入。'}")
        raise SystemExit(1) from None
