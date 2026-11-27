"""将本机隔离 MySQL 配置传给验收进程，不把口令放到命令行。"""
import json
import os
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
config = root / 'tmp' / 'mysql-databases.json'
environment = dict(os.environ)
if config.exists():
    for name, value in json.loads(config.read_text(encoding='utf-8-sig')).items():
        if name.isupper():
            environment.setdefault(name, value)
environment['PYTHONIOENCODING'] = 'utf-8'
if not sys.argv[1:]:
    raise SystemExit('用法：python tools/run-with-mysql.py -m pytest；或 ... node tools/run-browser-checks.cjs')
command = sys.argv[1:] if sys.argv[1] == 'node' else [sys.executable, *sys.argv[1:]]
raise SystemExit(subprocess.run(command, cwd=root, env=environment).returncode)
