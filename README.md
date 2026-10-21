# Everhere 人生相册 Web

使用 Python / Flask、MySQL 和原生 HTML / CSS / JavaScript，中文注释。现有核心记录流程参照安卓版，桌面侧栏和手机五项导航适配同一份资料。

本次交付记录：[v1.0 更新记录](CHANGELOG.md)。

协作先读 [开发大纲](agent.md)、[产品总规划 v3](docs/product-plan-v3.md)、[功能完成度与问题](docs/feature-completion.md)。完整规划包含未来路线，不代表全部实现。

## 在 VS Code 真实运行

1. 打开整个项目文件夹，安装 Microsoft **Python**、**Python Debugger** 扩展，选择 `.venv` 解释器。
2. 初次安装：`python -m venv .venv`，再运行 `.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt`。
3. 启动本机 MySQL。按 F5 选择“人生相册：MySQL 真实运行”，或执行 `.\.venv\Scripts\python.exe run.py`。
4. 没有 `.env` 时，终端引导创建新库和专用账号，管理员用户名默认 root、端口3306，密码隐藏输入，不写入文件；已有配置直接使用。向导不覆盖已存在的库。
5. 启动会验证真实 MySQL 并执行迁移，然后访问 `http://127.0.0.1:5000/`。**无需创建管理员或本地账户**。云登录是独立能力，不会上传人生资料。

当前安装 `.env` 已配置。更换端口可在 `.env` 设置 `WEB_PORT=5001`。停止按 Ctrl+C 或 VS Code 停止按钮。`run.py` 用于本机调试；正式部署使用 `wsgi.py` / Waitress 并通过发布流程迁移。

## 当前可用

三种创作状态、独立完成状态、五种日期精度、统一查询、时间轴/日历/全部记录/地点列表；记录和人物草稿、原 ID 编辑、回收站；人物聚焦与关联；最多10张原图、全屏浏览；暖阳/林间主题；Android普通JSON/原图ZIP导出及预览恢复，缺图确认、冲突复制、原字节校验。

已移除旧本地账户、保险箱、旧对象/线索/阶段管理、旧 Web 归档格式及演示库功能。按用户授权已清空历史资料和旧备份，未保存副本。

## 数据与云

Web资料存于当前 Flask/MySQL 安装；手机继续原 SQLite/SQLCipher，不改手机配置。浏览器签名 Cookie 对应一个独立本机空间，云登录不改变资料归属。**清理 Cookie 后，目前没有找回该本机空间的界面**，请先通过数据管理导出资料。Web不是浏览器离线库，MySQL普通资料及照片未实现端到端加密；远程部署后资料位于服务器。

`.env` 中 `CLOUD_API_URL` 留空不会连接云服务；`CLOUD_REGION=cn` 或 `global` 必须与安卓归档/账号区域一致。当前只有共同账号登录 BFF；共同后端缺少权益与范围许可，**云上传下载保持关闭**。注册/真实发信/找回/会话续期/双端联网未交付，见 [云边界](docs/cloud-sync.md)。

普通 JSON 不含原图；完整 ZIP 必须所有原图可读取且摘要校验正确。Web单次归档128MiB，JSON16MiB，单图50MiB/100MP。MySQL `max_allowed_packet` 需至少64MiB，Compose已设置64M。不要将独立备份与同步混同。

## 手动配置与部署

复制 `.env.example` 为 `.env`，填写独立随机 `SECRET_KEY` 与 `DATABASE_URL`。密码包含特殊字符时需URL编码；也可使用 `MYSQL_HOST`、`MYSQL_PASSWORD`。已有数据库使用版本化迁移：

```powershell
.\.venv\Scripts\python.exe -m flask --app wsgi db upgrade
.\.venv\Scripts\python.exe -m flask --app wsgi db check
.\.venv\Scripts\python.exe run.py
```

本轮迁移终点 `20261020_remove_legacy` 删除旧 users 表与私密字段；存在旧账户/受保护记录时会拒绝，须先按项目维护授权处理，迁移不会替你备份或暗中删除。不要删除已经执行的迁移链。

Docker可使用 `docker compose up --build`，需在 `.env` 设置 `SECRET_KEY`、`MYSQL_PASSWORD`、`MYSQL_ROOT_PASSWORD`。生产另需HTTPS、可靠限速存储、运维及访问控制；本轮未部署公网。

## 验证

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe tools/run-check-server.py
# 在另一终端设置 NODE_PATH 指向含 playwright 的目录，再执行：
node tools/browser-check.cjs
```

浏览器脚本使用已安装 Edge，默认连接5003的独立合成SQLite库；结束服务会释放内存库。测试夹具来自安卓导出器的合成样本，无真实用户资料。MySQL业务全套测试只允许专用 `_test` 库：设置 `TEST_DATABASE_URL` 后运行 pytest；不得指向业务库。接口见 [API](docs/api.md)，本轮实际证据见 [验收记录](docs/verification.md)。
