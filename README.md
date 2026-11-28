# Everhere Web

Everhere 提供私人相册、回忆录审核制作和独立文创商城。当前主线是 `main`；本次功能核对以五页设计报告的 **F1–F5** 为基准。

截至 2026-11-28，F1/F2/F4 核心已实现，F3 已有审核和制作但审批后需单独触发生成；F5 已有沙箱交易、退款和下载实现，仍缺首次完整下载记账、逐项取消和业务审批拒绝规则，本次重建环境已通过渠道查单验签，尚待实际交易验收。支付宝沙箱此前已验证可用，正式站支付关闭；两者均不代表 F5 全部完成。

- [当前需求](docs/requirements.md)
- [按报告逐项核对的完成度](docs/feature-completion.md)
- [报告范围与历史批次](docs/report-f1-f4-scope.md)
- [当前验证记录](docs/verification.md)
- [共用身份与同步发布](docs/public-album-sync-release.md)
- [支付宝沙箱与部署状态](docs/web-product-p4-alipay.md)

## 当前入口

| 路径 | 内容 |
|---|---|
| `/`、`/album`、`/records/<id>` | 私人记录、照片、草稿、时间轴、日历、人物和回收站 |
| `/account` | 注册、登录、验证、找回、设备会话、明确认领访客空间 |
| `/memoirs`、`/memoirs/<id>` | 最多 20 条记录选材、章节/照片授权、快照提交、修订及样张 |
| `/admin/memoirs` | 独占领取、审核/退回、固定版式制作与失败重试 |
| `/shop`、`/shop/products/<id>` | 独立商品、规格、定制文字和授权照片、电子/纸质回忆录选项 |
| `/orders`、`/orders/<id>`、`/admin/orders` | 本人订单和管理员分配处理，区分处理、付款、履约状态 |
| `/admin/products` | 商品、价格、上下架、封面和图库 |
| `/places`、`/connections` | 地点列表/WebGL 地球模型、现有记录与人物关联探索 |
| `/v1/auth/*`、`/v1/sync/*`、`/v1/assets/*` | 共用身份、Android 相册同步、原图传输 |

管理员仅访问分配给自己的授权稿件/订单材料，不得浏览无关相册或改写来源记录。普通商品不要求先有回忆录。样张与完整 PDF 下载分开授权。

地球尚未标记真实事件点位；没有多模板库、AI 草稿或宠物/影音业务。旧 cloud/archive/lifegraph API 和主题切换仍不开放，不能与新同步/关联探索入口混淆。

## 本机运行

需要 Python 3.12、MySQL 及独立的本机配置。新克隆不含 `.env`、私钥、数据库或虚拟环境，首次启动由 MySQL 向导配置专用库和账号。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe run.py
```

默认访问 `http://127.0.0.1:5000/`；前端无需构建。管理员交互创建，密码不写入文档：

```powershell
.\.venv\Scripts\python.exe -m flask --app wsgi create-admin
```

现有迁移头是 `20261125_album_sync`。部署先核对备份恢复和实际运行配置，再追加升级和检查；不得在真实资料库运行会清表的测试。

```powershell
.\.venv\Scripts\python.exe -m flask --app wsgi db upgrade
.\.venv\Scripts\python.exe -m flask --app wsgi db check
```

## 支付与环境

`ALIPAY_MODE` 默认 `disabled`；另有 `sandbox` / `production`，沙箱可承载报告要求的无实际扣款模拟付款，界面应明确标识测试环境。启用渠道后，完整下载、退款和履约仍由订单归属、可信渠道结果与状态约束控制。现有代码未实现报告的首次下载后禁止取消，详见完成度 F5。

正式站、本机、支付宝沙箱和自动化验收统一使用 MySQL，环境间使用不同库名和专用账号，详见 [数据库环境](docs/mysql-environments.md)。独立测试站 [sandbox.wyever.com](https://sandbox.wyever.com/shop) 已完成 DNS/HTTPS，商城无需额外入口密码；网站账号登录和管理员权限照常生效。2026-11-28 已配置沙箱参数并通过渠道只读查单验签，仍待买家实际付款、异步通知及退款验收。

## 验证

```powershell
.\.venv\Scripts\python.exe tools/run-with-mysql.py -m pytest
```

先在被 Git 忽略的 `tmp/mysql-databases.json` 或环境变量配置专用连接；MySQL 测试仅连接名称以 `_test` 结尾的隔离库，迁移测试再使用另一专用库。前端检查需要已安装 Playwright 和 Edge；通过 `python tools/run-with-mysql.py node tools/run-browser-checks.cjs` 启动独立合成服务，覆盖相册、语言和回忆录/商城流程。额外脚本见 `tools/product-experience-browser-check.cjs` 和 `tools/shared-identity-browser-check.cjs`。

CI 检查、隔离浏览器、公网页面、真实邮件、Android 真机和支付渠道证据分别记录。密钥和业务配置只放 `.env` 或 Git 忽略的测试目录，不提交私人资料或测试凭据。
