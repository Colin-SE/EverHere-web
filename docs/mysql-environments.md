# MySQL 环境与隔离

更新：2026-11-27。按用户要求，Web 的日常运行、支付宝沙箱、pytest、迁移和浏览器验收统一使用 MySQL，不再回退 SQLite。Android 客户端数据库不在本仓库改动范围内。

| 用途 | MySQL 库名 | 连接配置 |
|---|---|---|
| 正式站 | `life_album` | 正式服务 `.env` |
| 本机普通应用 | `life_album_local` | 本机 `.env` |
| 服务器支付宝沙箱 | `life_album_alipay_sandbox` | 服务器 `tmp/alipay-p4/database.json` |
| 本机支付宝沙箱 | `life_album_local_sandbox` | 本机 `tmp/alipay-p4/database.json` |
| pytest 业务验收 | `life_album_acceptance_test` | `TEST_DATABASE_URL` |
| 独立迁移验收 | `life_album_migration_test` | `IDENTITY_MIGRATION_TEST_URL` |
| 相册/语言浏览器验收 | `life_album_browser_test` | `BROWSER_DATABASE_URL` |
| 回忆录/商城浏览器验收 | `life_album_workflows_test` | `WORKFLOWS_DATABASE_URL` |
| 共用账号浏览器验收 | `life_album_identity_browser_test` | `IDENTITY_BROWSER_DATABASE_URL` |

各库使用专用数据库账号，仅授权对应库。服务器 MySQL 只通过回环访问；本机经 SSH 的 `127.0.0.1:13316` 转发至服务器 `127.0.0.1:3306`，不开放公网 MySQL 端口。本机转发断开时需先恢复转发再启动应用。

```powershell
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:13316:127.0.0.1:3306 nailoong
```

连接字符串只保存在忽略的 `.env`、`tmp/mysql-databases.json` 和沙箱 `database.json` 中，不写入仓库或命令行。`run-with-mysql.py` 将 JSON 中的大写环境变量传给子进程；自行准备环境时可直接设置同名变量。CI 使用临时 MySQL 容器中的 `life_album_test` 和 `life_album_migration_test`，不连接上述业务库。

```powershell
.\.venv\Scripts\python.exe tools/run-with-mysql.py -m pytest
.\.venv\Scripts\python.exe tools/run-with-mysql.py node tools/run-browser-checks.cjs
```

清表和重建仅限专用 `_test` 库，不能指向日常库或沙箱购买资料库。应用工厂拒绝非 MySQL 后端；沙箱还要求库名以 `_sandbox` 或 `_test` 结尾。迁移验收必须使用另一专用库。

两个新建沙箱从 SQLite 迁入 MySQL 时，逐表核对 31 张表、6 条业务资料；图片/文件按字节摘要核对，JSON 按规范化内容核对，时间按现有 MySQL 字段的秒精度保存。迁移校验结果放在各自忽略的 `tmp/alipay-p4/mysql-migration-verification.json`。正式库没有被清空或重新导入。

测试站使用直接的 Flask 网站权限，不增加 HTTP Basic 入口密码。匿名访客可打开商城，订单使用网站账号，后台保留管理员授权。网站管理员凭据在受保护的 `test-access.json`；该文件不再包含入口用户名或入口密码。
