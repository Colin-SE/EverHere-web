# 当前验证记录

更新：2026-11-27。评估基线为 main 的业务提交 `378ddc4b1ca6884c4247ccec64bf8500a06b17a1`，对照用户提供的五页设计报告。此次功能分析为代码和证据核对，没有补做报告缺失功能。

## 后续更新：统一 MySQL 与取消入口密码

本次数据库改造基线为 `7d89b71`，包括应用、沙箱、pytest/迁移和浏览器专用库、MySQL CI。所有环境的库名与账号分开，见 [数据库环境](mysql-environments.md)。下方 SQLite/入口认证记录是改造前的历史，不代表当前配置。

- 服务器独立 MySQL 全套：**142 passed、0 skipped**（68.67 秒），含独立迁移库、身份并发、相册同步及支付宝合成签名/退款流程。
- 本机普通库追加迁移至 `20261125_album_sync`，`flask db check` 报告无新升级操作。
- 本机和服务器两个沙箱各迁入 31 张表、6 条业务资料，逐表内容核对通过，时间按现有字段的秒精度保存。
- 本机与公网沙箱 health 为 MySQL/ok；匿名 `/shop` 为 200，无 WWW-Authenticate；未登录管理员商品接口为 401，账号权限仍生效。
- Edge 的相册、中英文、回忆录/商城、商品体验和共用账号流程已在各自独立 MySQL 验收库通过，覆盖断网编辑、照片上传、订单重试、地球降级、注册、重置密码和会话撤销。语言切换和商品体验检查增加等待视图/编辑器就绪，避免在初始化途中读取标题或操作尚未打开的表单。

这些自动化检查未使用真实支付宝收银台或实际通知。2026-11-28 用户完成控制台配置并提供参数，本机和服务器对不存在订单的渠道查询均验签通过，返回 `40004 / ACQ.TRADE_NOT_EXIST`；服务器已重启并输出 `Alipay configured`。用户随后确认“验收成功”；服务器只读核对到一笔 ¥1.00 `paid` 沙箱订单和 `alipay_notice`、`paid` 事件，库存从 12 到 11。付款及异步通知已确认；该订单无退款记录，退款、账单等不从总体结论推断。现已读取 `assignment requirements/` 并进入 [Milestone 2 整体规划](milestone-2-plan.md)。

## Milestone 2 当前准备

已完整提取并渲染核对课程要求 PDF，共 1 页；提交物为一个不超过 10 分钟的团队 MP4，每位成员英语说明姓名、贡献、设计理由和测试策略，并添加两位教师到 GitHub 仓库。用户已明确 HeSicheng、CuiChenshuo、CongZheming 的职责方向，具体视频分工见 [整体规划](milestone-2-plan.md)。未发现已完成的 MP4；精确截止时间、个人讲稿及教师访问尚待确认。

[017b932 的 CI](https://github.com/Colin-SE/EverHere-web/actions/runs/46098234584) 已核对为 success，MySQL 迁移与业务测试步骤成功。本次为只读验收与规划文档，没有重新运行或新增测试数量。

## 自动化与浏览器

| 证据 | 结果及边界 |
|---|---|
| [378ddc4 的 CI](https://github.com/Colin-SE/EverHere-web/actions/runs/46009856007) | SQLite business and permission tests、MySQL migration and business tests 均 success；已查询 job/step 状态。 |
| 本会话之前的 SQLite 全套 | 在含同步及账号冷却修复的业务基础上 127 passed、7 skipped，跳过项需要 MySQL 锁/独立迁移库；之后主题和图标不改业务。不是本次文档任务新跑的测试。 |
| Edge 隔离合成环境 | 相册/草稿/原图/回收站、语言、回忆录审核退回重提制作、样张、商城下单、订单往返、断网/重试和账号流程已通过。 |
| 公网页面 | 两域名 HTTPS health、暖色资源、顶部筛选、账号找回入口、备案号、品牌图标和 390px 布局已检查，无未处理页面脚本错误。 |

核心行为入口：`tests/test_workflows.py`、`tests/test_report_scope.py`、`tests/test_product_experience.py`、`tests/test_shared_identity.py`、`tests/test_shared_identity_concurrency.py`、`tests/test_album_sync.py`、`tests/test_alipay_commerce.py`。合成签名网关测试不等于真实支付宝回调或资金验收。

## 生产只读核对

2026-11-27 通过既有 SSH 以服务账户检查：

- `everhere` 服务 active，运行目录 `/home/admin/apps/everhere-web`，业务提交 `378ddc4`。
- MySQL 迁移头 `20261125_album_sync`；共用身份和相册同步开启，支付宝 disabled。
- `https://wyever.com/health` 返回 MySQL/ok。
- 当次数据库查询没有上架商品规格或 ready 回忆录；首版购买/交付演示数据尚需准备。

没有在生产库运行 pytest、清表或测试种子，没有因更新文档修改正式支付开关。

## 支付宝沙箱历史与本次重建

用户在本次对话确认：支付宝沙箱此前已验证可用。保留此项历史结论；具体付款、异步通知、退款和账单的完成程度仍按各自证据登记。

检查时，旧本机 `tmp/alipay-p4`、密钥、测试库和虚拟环境已按此前要求清空；没有 15044 监听及临时隧道。生产站没有配置或启用支付宝。这不说明支付宝控制台中的沙箱应用失效。

随后按用户要求：重建本机 `.venv` 并安装锁定依赖，生成且校验 RSA2 公私钥；启动独立 SQLite 服务，本机 health 200、匿名 shop 401、入口认证 shop 200。Cloudflare Quick Tunnel 申请返回 429，未获得新公网地址。

在重建的本机环境定向运行 `tests/test_alipay_commerce.py`：4 passed、1 skipped（须 MySQL 行锁），验证签名与交易/退款逻辑；该组使用合成签名网关，未向支付宝发起真实付款，不能代替控制台参数配置。

用户又要求服务器部署；已创建独立 worktree `/home/admin/apps/everhere-alipay-sandbox` 和 systemd 服务 `everhere-alipay-sandbox`。服务复用现有只读 Python 依赖，但使用独立测试库、密钥和入口口令，监听 `127.0.0.1:15044`；服务器回环检查 health 200、匿名 shop 401、入口认证 shop 200。正式服务不受影响。

用户完成 DNS 后，已为 `sandbox.wyever.com` 签发独立证书（到期 2027-02-25，自动续期）并配置 Nginx。公网 HTTPS health 200、匿名 shop 401，正式站 health 200。入口认证在服务器回环验证，不通过公共隧道传送凭据。

以上为重建早期状态。后续参数配置、查单验签及本次付款/通知结果见本文开头和支付文档，不再把早期 awaiting configuration 作为当前状态。

## 未完成与待验收

- 报告 F5 的首次下载记账、逐项取消资格及业务审批拒绝，以及本次尚缺证据的退款、电子交付及履约端到端复验。
- F3 审批是否自动触发生成，与报告的触发描述对齐。
- 真实 Android 真机、弱网/冲突/换机/换号的联合验收证据；公网认证 401 不等于真机同步成功。
- 本次沙箱付款及通知已有证据；退款、账单和电子版交付仍需逐项复验，正式支付/实际印刷/自动物流未开放。
- Milestone 2 视频、成员英文讲解和老师仓库访问须单独确认。

逐项要求和证据见 [完成度](feature-completion.md)。旧日期的 F1–F4、账号或验收记录是历史快照，不能覆盖本文件的当前结论。
