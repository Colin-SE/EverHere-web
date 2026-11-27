# P4 支付宝网页交易

## 当前状态 2026-11-27

用户确认支付宝沙箱此前已验证可用。清空并重新克隆项目后，旧本机配置、密钥和测试库已不存在；本次已重新生成 RSA2 密钥并校验公私钥匹配，安装锁定依赖，重建独立测试服务。新应用公钥须在原沙箱应用中重新上传；AppID、沙箱商家 PID 和支付宝公钥尚待控制台提供。

本机服务在 `127.0.0.1:15044`，使用独立 SQLite 和入口口令。本机 health/匿名拒绝/授权入口检查通过。Cloudflare Quick Tunnel 申请返回 429，未取得新地址。

用户随后要求部署服务器。独立代码目录为 `/home/admin/apps/everhere-alipay-sandbox`，服务为 `everhere-alipay-sandbox`，数据库和密钥在该目录的 `tmp/alipay-p4/`；复用正式服务的 Python 依赖，但不使用正式数据库或正式配置。服务已启动，服务器回环 health 200、匿名商城 401、授权商城 200。

计划公网入口为 `https://sandbox.wyever.com`。该地址尚需添加 A 记录 `sandbox -> 47.93.252.27`、申请子域名证书并配置 Nginx，不能当成已经可访问。原证书仅覆盖 wyever.com / www.wyever.com。正式站支付宝仍为 disabled，没有改为沙箱或真实支付。

新应用公钥文件是本机 `tmp/alipay-p4/upload-this-app-public-key.txt`，商户私钥只保存在受保护配置目录，不发到聊天或仓库。控制台采用 RSA2 普通公钥模式；应用公钥是上传到支付宝的文件，支付宝公钥是下载到服务端用于验签的另一把公钥。

完成域名和参数后，重启独立服务并核对启动输出 configured，再分别验证签名查单、收银台、付款、通知、退款和账单。不把“此前沙箱可用”扩大成每个子项都已复验，支付宝沙箱可承载报告的模拟支付，但渠道可用不能替代 F5 的首次下载和取消规则验收。报告缺口见 [完成度 F5](feature-completion.md#f5-结算与交付原型)。

以下为本机工具和既有交易规则。它们描述配置方式，不代表当前公网/付款已经接通。

## 测试站

测试站绑定本机 `127.0.0.1:15044`，使用 `tmp/alipay-p4/sandbox.sqlite3`、独立会话密钥、合成管理员和 ¥1.00 示例商品。全部测试环境文件位于 Git 忽略的 `tmp/alipay-p4/`。测试商城与管理后台使用该目录下 `test-access.json` 的入口口令，支付宝通知路径和健康检查可直接访问。真人付款只在支付宝沙箱买家收银台操作。

1. 执行 `python tools/alipay-sandbox-server.py --prepare` 准备隔离配置和 RSA2 密钥。上传给支付宝的文件为 `upload-this-app-public-key.txt`，应用私钥留在 `merchant-private.pem`。
2. 在 [支付宝沙箱控制台](https://open.alipay.com/develop/sandbox/app) 查看沙箱应用 ID、沙箱商家 PID 和沙箱买家账号。选择普通公钥 RSA2 模式，上传第 1 步生成的应用公钥。将控制台显示的支付宝公钥保存为 `alipay-public.pem`。
3. 在 `settings.json` 填写 `appId`、`sellerId`。若控制台指定旧版网关，`sandboxGateway` 可填官方网关 `https://openapi.alipaydev.com/gateway.do`。留空使用新版官方网关。
4. Cloudflare Quick Tunnel 指向 `http://127.0.0.1:15044`，把它分配的 HTTPS origin 写入 `origin.txt`。启动或重启 `python tools/alipay-sandbox-server.py` 后，以启动行的 `configured` 确认支付宝启用。每次换通道须同步 origin 并重启应用。应用生成的通知地址为 `{origin}/payments/alipay/notify`。
5. 用合成用户创建实体订单，填测试地址，用沙箱买家余额付款，回站核对状态。再用未开工订单测试退款，管理员领取后批准。在支付宝控制台核查同一商户单号和退款请求号。

## 交易边界

- 单个订单只生成一个支付宝交易号，设备重试复用相同的商户单号、金额和绝对到期时间。服务端用 RSA2 验签，核对应用、卖家、商户单号、交易号及金额。浏览器返回只触发服务端查单。可信支付状态由异步通知或签名查询更新。
- 签发收银台链接前冻结实体地址并预占有限库存。未跟踪库存的款式按不限量处理。限量库存以可售件数管理，关单和全额退款只释放一次。30 分钟到期，先查单再关单。关单后补到的付款进入人工核对和原路退款流程。
- 本轮的退款按整单全额处理。实体订单开工前可申请，由订单负责人审批。支付请求结果不明时，用原退款请求号核对再重试。已付款的电子回忆录按冻结版本交付，申请退款起撤销后续下载权限。
- 实体交付按开始制作、手工录入物流并发货、买家确认收货流转。P3 的客服处理状态继续独立。当前提供支付宝电脑网站收银台、手工物流记录和业务账单差异核对。部分退款、自动物流查询和独立售后退件流程后续按经营规则扩展。

## 正式部署与验收

正式配置默认 `ALIPAY_MODE=disabled`。先独立恢复备份和迁移至 `20261115_alipay_commerce`，使用 `flask db check` 验证结构，按正式商户配置填写 `.env.example` 中对应变量及专用密钥文件。启用前安排正式 HTTPS 回调、受限服务账户和周期任务 `flask --app wsgi expire-alipay-orders`，并验证重启后关单任务继续执行。测试站单独运行每 30 秒一次的关单检查。

支付宝业务账单下载后，解压中文交易明细 CSV。运行 `flask --app wsgi reconcile-alipay --date YYYY-MM-DD --bill {path}`，按北京时间自然日核对确认支付和退款记录。迟到的渠道结果可能形成跨日差异，使用原交易号和退款请求号复核。本命令只报告差异。

本地自动化通过隔离数据库和合成签名网关验收，覆盖签名、重复回调、关单晚到付款、并发付款、库存、退款重试、授权下载、分配后的发货和账单差异。真实收银台、支付宝发出的回调、沙箱退款与真实账单需提供相应沙箱或正式交易证据后逐项记录。

- [支付宝电脑网站支付接入](https://s.apifox.cn/apidoc/docs-site/3618910/doc-3271411)
- [支付宝业务账单说明](https://s.apifox.cn/apidoc/docs-site/3618910/doc-3270792)
- [Cloudflare Quick Tunnel](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)
