# 设计报告功能完成度

核对日期：2026-11-27。业务代码基线：`378ddc4b1ca6884c4247ccec64bf8500a06b17a1`，分支 `main`。本次核对不补做以下缺失功能。

依据用户提供的五页《Everhere: Life Album and Custom Memoirs — Design Report》（`main.pdf`）。第 1 页定义首版边界，第 2 页定义 F1–F5 与 O1–O5，第 3–4 页定义流程和一致性，第 5 页定义技术及验证。原 PDF 的 SHA-256 为 `b2e9fed06ddaba6a620769bf21e75fd19948f3f18b3b2e4bdebbcc2ba0e2bcf7`。报告是需求证据，不是完成证据。

## 结论与口径

F1、F2、F4 的核心功能已有实现；F3 已有审核、固定版式制作、样张和失败恢复，但审批与触发生成分为两步。F5 已有沙箱交易、退款和下载实现，尚缺部分取消约束，本次重建环境也仍待接通。支付宝沙箱此前已验证可用，由用户在本次核对中确认；生产支付关闭、当前重建沙箱环境、报告 F5 仍有规则缺口是不同事项。

“已实现”表示有代码和可定位的行为证据；“部分实现”表示缺少明确子流程或规则；“实现有差异”表示触发方式、技术或状态语义与报告不同；“待验收”表示尚缺实际使用证据；“未实现”表示没有可完成任务的业务路径。测试数量和表格行数不换算为产品完成百分比。

## F1 私人记录与浏览

来源：报告第 2 页 F1。

| 验收点 | 状态 | 当前实现与证据 |
|---|---|---|
| 创建、查看和编辑本人文字与照片记录 | 已实现 | `app/api/records.py`、`app/services/records.py`；稳定来源 ID 和归属检查。 |
| 保存/继续草稿、软删除及原 ID 恢复 | 已实现 | `app/api/drafts.py`、记录删除/恢复；`tests/test_application.py`、`tests/test_product_experience.py`。 |
| 时间轴、日历、人物、地点引用同一份记录 | 已实现 | 复用 LifeRecord 和关联；`tests/test_report_scope.py::test_places_include_names_without_coordinates_and_keep_owner_isolation`。 |
| 只有本人修改来源，日常记录不经管理员审批 | 已实现 | `app/security.py` 与记录/照片归属校验；投稿权限不开放原相册。 |
| 日/月/年/范围/未知日期，逾期计划不自动完成 | 已实现 | 日期结构校验；`test_overdue_plan_does_not_become_an_occurred_record`。 |

浏览器离线持久写入、完整保险箱和永久资源回收不属于本报告 F1 已交付范围。

## F2 整理与提交回忆录

来源：报告第 2 页 F2、第 3–4 页快照和修订。

| 验收点 | 状态 | 当前实现与证据 |
|---|---|---|
| 最多 20 条本人记录、主题、章节标题与顺序 | 已实现 | `app/services/memoirs.py::normalise_draft`、`app/static/js/workspace.js`。 |
| 保存草稿、修改退回稿，明确授权所选材料 | 已实现 | `app/api/memoirs.py`；保存与提交分开，提交需授权。 |
| 冻结正文、来源 ID/版本、顺序和所选照片字节 | 已实现 | `freeze`、MemoirRevision、MemoirAsset。 |
| 原相册编辑不改变已提交版本；重提保留旧审核版本 | 已实现 | `tests/test_workflows.py::test_two_roles_return_resubmit_generate_and_keep_immutable_selected_material`。 |

当前正文取自原记录，可修改章节标题及顺序。独立正文/封面编辑和按年/人物/地点选材属于另一份阶段任务单的扩展，尚未实现；它们不是这份报告 F2 的逐字要求，不能因此将整个 F2 判为未完成。

## F3 审核与制作

来源：报告第 2 页 F3、第 3 页流程、第 4 页一致性。

| 验收点 | 状态 | 当前实现与证据 |
|---|---|---|
| 队列、原子领取并保存 reviewer ID | 已实现 | `app/api/memoirs.py::claim`；`test_second_claim_is_rejected_and_original_reviewer_is_retained`。 |
| 仅领取人审核/制作，不改用户原始记录 | 已实现 | `app/services/memoirs.py::assigned`、快照及素材接口。 |
| 通过/附原因退回、顺序和字号排版、拒绝旧版本决定 | 已实现 | `review`、`generate`、`check_version`；改字由用户修改后重提。 |
| 审核通过开始生产 | 实现有差异 | 审核仅进入 `approved`；管理员再点击生成才入队，尚未实现报告描述的自动衔接。 |
| 固定版式 PDF、独立样张、付款前不开放完整 PDF | 已实现 | `memoir_pdf.py`、`memoir_jobs.py`；样张最多两页且至少省略一页；完整文件另走订单下载权限。 |
| 失败保留批准材料并可重试，不能伪造 ready | 已实现 | 成品/样张/ready 一致提交；`test_failed_generation_keeps_approved_snapshot_then_retries`、`test_sample_failure_does_not_mark_production_ready`。 |

## F4 独立商城

来源：报告第 2 页 F4、第 4 页订单快照。

| 验收点 | 状态 | 当前实现与证据 |
|---|---|---|
| 奖牌/礼品不依赖回忆录，可以独立下单 | 已实现 | `app/api/shop.py`；`test_ordinary_gift_order_is_independent_private_idempotent_and_price_snapshot`。 |
| 款式、文字或授权照片，冻结定制内容与照片字节 | 已实现 | ShopOrderItem；`test_custom_photo_requires_explicit_authorisation_and_is_frozen`、`test_order_keeps_photo_bytes_when_source_changes_and_blocks_other_users`。 |
| 本人 ready 回忆录选择电子/纸质规格 | 已实现 | `memoir_digital` / `memoir_paper`；`test_memoir_purchase_requires_own_ready_revision_and_active_variant`。 |
| 商品描述、价格、可用状态管理及无效输入阻止下单 | 已实现 | 商品/款式接口、服务端计价、字段错误和事务回滚。 |

当前照片入口为上传文件；直接从已有相册挑照片的入口尚缺。报告 F4 要求授权照片，没有明确指定该选图入口，另一份阶段任务单有此要求。

## F5 结算与交付原型

来源：报告第 1 页模拟边界、第 2 页 F5、第 3 页购买下载、第 4 页首次下载和取消规则。

| 验收点 | 状态 | 当前实现与缺口 |
|---|---|---|
| 服务端保存确认价格、数量、选项和成品版本 | 已实现 | 订单/素材快照和请求幂等，不随商品或原记录改变。 |
| 实体商品地址 | 已实现，当前环境待接通 | 支付宝沙箱 checkout 校验并冻结地址；正式站支付关闭。 |
| 明确标识的模拟付款/退款，无真实扣款 | 已有沙箱实现，待本次复验 | 用户确认沙箱此前可用；支付宝沙箱可承载无实际扣款的模拟付款。报告未要求必须自建模拟适配器；新环境须配置渠道并核对测试标识及完整购买/退款流程。 |
| 付款后本人下载冻结修订的完整 PDF | 已实现，生产停用 | `app/api/payments.py::download` 核对 paid、买家、电子项、修订和退款；合成签名网关测试通过。生产支付关闭，不能宣称可在线买到成品。 |
| 买家直接取消未付款订单 | 部分实现 | 已有 `/cancel`，但路由先要求配置支付宝；disabled 时不可用。状态为 `closed`，与报告 `cancelled` 不同。 |
| 已付款取消须批准、整单取消而非部分取消 | 部分实现 | 买家申请及受分配管理员整单全额退款已有；缺业务审批拒绝路径。渠道 `rejected` 不等于管理员拒绝申请。 |
| 电子项只能在首次完整下载前取消 | 未实现 | ShopOrderItem 没有首次下载时间/标记，下载路由不记账。现有测试在完整下载后仍申请并完成退款，不能证明此约束成立。 |
| 实体开工前取消，所有订单项逐项共同检查 | 部分实现 | 订单级 fulfillment 阻止开工/发货后退款；没有电子项首次下载与每个实体项生产状态的共同资格检查。 |
| 批准取消即暂停交付，失败保留暂停可重试，拒绝保持原单 | 部分实现 | 当前从申请阶段就阻止交付，提交退款进入 refunding；同退款号重试已有。审批时点、业务拒绝和模拟退款终态仍需对齐。 |
| 仅管理员更新模拟实体履约 | 已有实现，待本次复验 | 受分配管理员可开工/录入物流，买家确认收货；在沙箱订单中可演示状态流转，不触发实际印刷或派送。 |

F5 不能标记全部完成。优先完成沙箱重配与演示标识核对，补首次下载记账、逐项取消资格和审批拒绝，再验收完整路径。本文记录差异，不自动授权实现或改变退款政策。

## 可选功能 O1–O5

| 报告功能 | 状态 | 当前范围 |
|---|---|---|
| O1 宠物/影音日记 | 未实现 | 没有独立业务路径；保留协议字段不算实现。 |
| O2 更多模板和礼品规格 | 部分实现 | 可维护商品/款式和图库；仍为单套固定版式，无多模板库。 |
| O3 AI 辅助草稿 | 未实现 | 无选材总结、来源确认和 AI 生成业务。 |
| O4 在交互地球上探索定位记录 | 部分实现 | 有 WebGL 地球和地点列表；地球未显示真实事件点位。 |
| O5 真实支付、印刷、物流 | 部分实现 | 支付宝沙箱此前已验证可用（用户确认），有渠道签名/查单/退款及手工物流代码。生产支付关闭，没有实际印刷或自动物流的验收。 |

可选项不应先于 F5 缺口成为首版门槛。

## 架构与技术对照

- 已使用 HTML/CSS、Jinja、原生 JavaScript/Fetch、Flask、Flask-SQLAlchemy/PyMySQL/MySQL、Flask-Login/Werkzeug、ReportLab/Pillow/pypdf，无前端构建要求。
- 报告第 5 页提出 Flask-WTF/WTForms；当前为 JSON/字段校验和自定义会话 CSRF 检查，未使用这两项库。
- 报告的 User/Revision/Order/PaymentEvent 对应实际 Member/SpaceOwnership、MemoirRevision、ShopOrder/ShopOrderItem、OrderTrade/TradeEvent。命名不同不是功能缺失；首次下载字段确实缺少。
- 已有归属、任务分配、版本冲突、快照、唯一事件和事务控制；F5 首次下载与逐项取消的共同锁定策略尚缺。

## 部署与验证范围

2026-11-27 只读核对：正式站 `378ddc4`，迁移 `20261125_album_sync`，共用身份和相册同步开启，支付宝 disabled，健康正常。该次查询没有上架商品规格或 ready 回忆录；报告要求的一种纸质选项、独立纪念商品及可下载成品仍需准备实际演示数据。

当前业务提交的 [GitHub Actions](https://github.com/Colin-SE/EverHere-web/actions/runs/46009856007) 中 SQLite 和 MySQL 迁移/业务检查成功。本会话此前同一业务代码的 SQLite 全套为 127 通过、7 跳过，之后只改主题和图标；此次文档核对没有重跑业务全套，不能作为新的测试次数。

隔离 Edge 已覆盖相册、语言、回忆录审核制作、商城、订单和账号；公网验证覆盖健康、主题/图标、导航与移动布局。没有把 401 认证保护当作真机同步成功，也没有在本次检查重新收发真实邮件或付款。用户确认沙箱已可用；付款、通知、退款和账单的逐项证据分别记录，不从总体结论推断所有子项。

## 当前沙箱及其他任务

旧本机沙箱配置随用户要求的项目清空删除。用户随后授权重建，已重新生成密钥、安装独立环境，并在服务器启动 `everhere-alipay-sandbox` 独立 SQLite 服务。本机和服务器回环健康/入口认证已通过；公网子域名 DNS/证书仍待配置，接通渠道仍需上传新应用公钥并提供 AppID、商家 PID、支付宝公钥。当前进度见 [支付宝配置记录](web-product-p4-alipay.md)，历史已验证可用的结论保留。

11 月 25 日任务单中的独立用户管理、相册选图下单、回忆录正文/封面和筛选、Android 真机验收需另跟踪，不能替代或改写本报告 F1–F5。共用账号与同步代码已在 main 上线，真机结果仍待证据。Milestone 2 的团队 MP4、成员英文讲解及老师仓库权限也需单独确认，设计报告不证明这些已提交。
