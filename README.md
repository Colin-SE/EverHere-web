# Everhere Web — 设计报告 F1—F4

2026-11-08：按用户确认的 F1—F4 直接重构当前项目。保留私人相册、回忆录选材提交、管理员审核与固定版式制作、独立文创商城和待支付订单。F5 支付、取消退款与履约不在本次范围。

范围与删除项见 [设计报告功能对照](docs/report-f1-f4-scope.md)，验证见 [本轮验证记录](docs/report-f1-f4-verification.md)。旧 Android 总规划与历史验收说明不再作为当前功能范围。

## 功能入口

| 入口 | 功能 |
|---|---|
| `/` | 记录、照片、草稿、时间轴、日历、人物、地点与回收站 |
| `/workspace#account` | 网站注册、登录、退出；显式认领已有访客相册 |
| `/workspace#memoirs` | 最多 20 条记录选材、章节排序、选图授权、快照提交与进度 |
| `/workspace#admin` | 管理员领取、审核、退回、排版制作及商品管理 |
| `/workspace#shop` | 独立奖牌/礼品定制、本人已完成回忆录的电子/纸质选项 |
| `/workspace#orders` | 本人待支付订单与冻结的价格、文字和选项 |

相册、回忆录与商城并行。管理员只能读取自己领取的投稿材料，不能浏览或修改用户原始相册。回忆录只开放部分样张，完整 PDF 没有下载接口。普通商品不要求先创建回忆录。

已删除人生脉络、共同云连接、Android JSON/ZIP 导入导出和主题切换的用户界面、接口和专用源码。中英文显示、原有资料归属及历史数据库迁移继续保留。

## 本机运行

技术栈：Python / Flask、SQLAlchemy、MySQL、原生 HTML / CSS / JavaScript。PDF 使用 ReportLab 与 pypdf。前端无需构建。

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe run.py
```

已有 `.env` 配置会继续使用；首次运行由向导建立 MySQL 专用库和账号。访问 `http://127.0.0.1:5000/`。VS Code F5 也可启动。已有访客空间保持原签名 Cookie 归属，注册时明确勾选认领后才能将其绑定账户；登录已有账户不会自动合并资料。

管理员由服务器维护者创建，密码交互输入：

```powershell
.\.venv\Scripts\python.exe -m flask --app wsgi create-admin
```

保留现有迁移链，终点为 `20261102_product_images`，本次无数据库结构变动。手动部署前可执行：

```powershell
.\.venv\Scripts\python.exe -m flask --app wsgi db upgrade
.\.venv\Scripts\python.exe -m flask --app wsgi db check
```

连接信息和密钥只存本机 `.env`；不提交数据库、照片或私人资料。Web 数据保存在此安装的服务器数据库中，需要服务运行才能访问。

## 验证

```powershell
.\.venv\Scripts\python.exe -m pytest
# 先启动独立内存库；另一终端运行相册和语言验收
.\.venv\Scripts\python.exe tools/run-check-server.py
npm run test:browser
npm run test:i18n
```

跨角色回忆录和商城流程使用另一独立服务：

```powershell
.\.venv\Scripts\python.exe tools/workflows-check-server.py
# 另一终端
npm run test:workflows
```

需要已安装 playwright 和 Edge。MySQL 业务测试只允许名称以 `_test` 结尾的隔离库，不得把 `TEST_DATABASE_URL` 指向真实资料库。浏览器脚本只允许指定本机端口并检查 SQLite 健康响应。Docker 可通过 `docker compose up --build` 启动，正式部署使用 `wsgi.py` / Waitress。

Windows 下也可运行 `npm run test:browser:all`，由脚本在同一执行环境启动两个合成服务、依次完成三组浏览器验收并关闭子进程。默认使用 `.venv\Scripts\python.exe`，可通过 `TEST_PYTHON` 指定其他解释器。
