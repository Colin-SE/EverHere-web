"""本地初始化的隔离检查：不连接真实数据库，不保存管理员密码。"""

import json
import os
from pathlib import Path

import pymysql
import pytest
from dotenv import dotenv_values
from sqlalchemy.engine import make_url

from scripts import setup_mysql


class Cursor:
    def __init__(self, existing=False):
        self.existing = existing
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def execute(self, statement, arguments=None):
        self.calls.append((statement, arguments))

    def fetchone(self):
        return ("existing",) if self.existing else None


class Connection:
    def __init__(self, cursor=None):
        self.active_cursor = cursor or Cursor()
        self.closed = False

    def cursor(self):
        return self.active_cursor

    def close(self):
        self.closed = True


@pytest.fixture
def setup_directory():
    # 使用项目可写目录，避免 Windows 受限临时目录影响测试。
    from tempfile import TemporaryDirectory
    target = Path(__file__).resolve().parents[1] / "instance"
    target.mkdir(exist_ok=True)
    with TemporaryDirectory(dir=target, prefix="setup-check-") as directory:
        yield Path(directory)


@pytest.mark.parametrize("name", ["mysql", "sys", "information_schema", "performance_schema", "bad-name", "bad_name", "a`;DROP DATABASE mysql;", "1name", ""])
def test_rejects_invalid_or_system_database(name):
    with pytest.raises(setup_mysql.SetupError):
        setup_mysql.validate_database_name(name)


def test_setup_only_grants_project_database_and_hides_admin_password(setup_directory, capsys):
    target = setup_directory / ".env"
    admin, application = Connection(), Connection()
    connections = iter([admin, application])
    calls = []

    def connect(**kwargs):
        calls.append(kwargs)
        return next(connections)

    setup_mysql.provision(admin_user="root", admin_password="admin-secret-not-to-store", database="lifealbumweb", env_path=target, connect=connect)
    values = dotenv_values(target)
    url = make_url(values["DATABASE_URL"])
    assert url.drivername == "mysql+pymysql"
    assert url.database == "lifealbumweb" and url.host == "127.0.0.1"
    assert url.username != "root" and len(url.password) >= 32
    assert len(values["SECRET_KEY"]) >= 32
    assert "admin-secret-not-to-store" not in target.read_text(encoding="utf-8")
    assert "admin-secret-not-to-store" not in capsys.readouterr().out
    assert calls[1]["user"] == url.username and calls[1]["password"] == url.password
    statements = [statement for statement, _ in admin.active_cursor.calls]
    grant = next(statement for statement in statements if statement.startswith("GRANT"))
    assert "ON `lifealbumweb`.*" in grant and "ON *.*" not in grant
    assert "WITH GRANT OPTION" not in grant
    assert admin.closed and application.closed


def test_existing_environment_is_never_overwritten(setup_directory):
    target = setup_directory / ".env"
    target.write_text("EXISTING=keep\n", encoding="utf-8")
    with pytest.raises(setup_mysql.SetupError):
        setup_mysql.provision(admin_user="root", admin_password="secret", database="lifealbumweb", env_path=target, connect=lambda **kwargs: pytest.fail("不应连接数据库"))
    assert target.read_text(encoding="utf-8") == "EXISTING=keep\n"


def test_existing_database_is_never_modified(setup_directory):
    admin = Connection(Cursor(existing=True))
    with pytest.raises(setup_mysql.SetupError):
        setup_mysql.provision(admin_user="root", admin_password="secret", database="lifealbumweb", env_path=setup_directory / ".env", connect=lambda **kwargs: admin)
    assert len(admin.active_cursor.calls) == 1
    assert not (setup_directory / ".env").exists()
    assert admin.closed


def test_connection_failure_does_not_echo_password_or_create_config(setup_directory, capsys):
    def unavailable(**kwargs):
        raise pymysql.OperationalError(1045, "sensitive-driver-detail")

    with pytest.raises(setup_mysql.SetupError, match="用户名或密码不正确") as error:
        setup_mysql.provision(admin_user="root", admin_password="private-password", database="lifealbumweb", env_path=setup_directory / ".env", connect=unavailable)
    assert "sensitive-driver-detail" not in str(error.value)
    assert "private-password" not in capsys.readouterr().out
    assert not (setup_directory / ".env").exists()


def test_vscode_launch_runs_real_mysql_entry():
    root = Path(__file__).resolve().parents[1]
    launch = json.loads((root / ".vscode" / "launch.json").read_text(encoding="utf-8"))
    default = launch["configurations"][0]
    assert default["program"] == "${workspaceFolder}/run.py"
    assert default["env"]["APP_MODE"] == "mysql"
    assert default["console"] == "integratedTerminal"


def test_launcher_cancels_missing_input_without_claiming_success(monkeypatch, capsys):
    import run
    monkeypatch.setattr(run, "prepare_application", lambda: (_ for _ in ()).throw(EOFError()))
    assert run.main() == 1
    output = capsys.readouterr().out
    assert "未启动" in output and "已准备就绪" not in output
