# 当前验证记录

更新：2026-11-27。评估基线为 main 的业务提交 `378ddc4b1ca6884c4247ccec64bf8500a06b17a1`，对照用户提供的五页设计报告。此次功能分析为代码和证据核对，没有补做报告缺失功能。

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

当前仍需控制台上传新应用公钥、填写 AppID/商家 PID/支付宝公钥。未获得参数前服务为 awaiting configuration，不得写成付款已经重新接通。

## 未完成与待验收

- 报告 F5 的首次下载记账、逐项取消资格及业务审批拒绝，以及重建后沙箱模拟支付/退款/履约的端到端复验。
- F3 审批是否自动触发生成，与报告的触发描述对齐。
- 真实 Android 真机、弱网/冲突/换机/换号的联合验收证据；公网认证 401 不等于真机同步成功。
- 本次重建后的渠道签名查单、收银台、通知、退款和账单逐项复验；正式支付/实际印刷/自动物流未开放。
- Milestone 2 视频、成员英文讲解和老师仓库访问须单独确认。

逐项要求和证据见 [完成度](feature-completion.md)。旧日期的 F1–F4、账号或验收记录是历史快照，不能覆盖本文件的当前结论。
