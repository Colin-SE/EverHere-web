"""为 F1—F4 创建唯一的隔离 MySQL 测试库，结束后只删除本进程新建的库。"""
import argparse
import os
from pathlib import Path
import re
import subprocess
import sys
from uuid import uuid4

from dotenv import dotenv_values
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

parser = argparse.ArgumentParser()
parser.add_argument('--env-file', default='.env')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
config = dotenv_values(Path(args.env_file))
uri = config.get('DATABASE_URL')
if not uri:
    raise SystemExit('配置中没有 MySQL 连接，未执行数据库写入。')
url = make_url(uri)
if url.get_backend_name() != 'mysql':
    raise SystemExit('此检查只接受 MySQL 配置。')
database = 'everhere_f1f4_' + uuid4().hex[:12] + '_test'
assert re.fullmatch(r'everhere_f1f4_[a-f0-9]{12}_test', database)
assert database != url.database
server = create_engine(url.set(database=None), isolation_level='AUTOCOMMIT')
created = False
result_code = 1
try:
    with server.connect() as connection:
        connection.exec_driver_sql(f'CREATE DATABASE `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
        created = True
    environment = {**os.environ, 'TEST_DATABASE_URL': url.set(database=database).render_as_string(hide_password=False), 'PYTHONIOENCODING': 'utf-8'}
    # 所有测试固定使用刚建立的 _test 库，不对原数据库迁移或清表。
    result_code = subprocess.run([sys.executable, '-m', 'pytest', '-o', 'addopts=', '-q'], cwd=root, env=environment).returncode
except SQLAlchemyError as error:
    code = getattr(getattr(error, 'orig', None), 'args', (None,))[0]
    print('无法建立隔离 MySQL 测试库：' + type(error).__name__ + '，错误码 ' + str(code) + '。未修改原资料库。')
finally:
    if created:
        with server.connect() as connection:
            connection.exec_driver_sql(f'DROP DATABASE `{database}`')
        print('本进程的隔离测试库已删除。')
    server.dispose()
raise SystemExit(result_code)
