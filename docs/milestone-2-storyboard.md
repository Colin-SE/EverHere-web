# Milestone 2 详细分镜与双语口播稿

版本：2026-11-28，已按课程 PDF 复核修订。基于 [整体规划](milestone-2-plan.md) 及当前已核对的 Beta。目标成片 **09:35**，共 **19 个镜头段**。以下时码是剪辑安排，不是已经实测的朗读时长；录音后需按真实语速微调，最终 MP4 不超过 10 分钟。逐项检查见 [要求与逻辑链复核](milestone-2-script-review.md)。

英文引文是需要朗读的正文；中文释义、操作说明、字幕和代码路径不朗读。每人独立提词稿见文末链接。三人的职责采用已确认分工，口播用“负责／主导”描述模块，不声称某个人独立编写了所有相关代码或测试。

主版本英文约 944 词。按每分钟约 110–125 词朗读，正文约需 7 分 33 秒至 8 分 35 秒，其余时间用于页面操作、结果停留和交接。朗读可以与操作同时进行，不能将全部操作时长再机械相加。历史付款备用段不与主版本连读，也未重复计入主稿词数。

| 成员 | 英文词数（约） | 分配画面时间 | 出场镜头 |
|---|---:|---|---|
| HeSicheng | 332 | 3:20 | S01、S06–S09、S16、S19 |
| CuiChenshuo | 305 | 3:10 | S11–S15、S17 |
| CongZheming | 307 | 3:05 | S02–S05、S10、S18 |

## 录制前布置

### 统一环境与故事

- 网站：`https://sandbox.wyever.com`。付款使用支付宝沙箱，MySQL 使用独立 `life_album_alipay_sandbox` 库。正式站和沙箱账号分开。
- 网页界面建议切到 English；本稿操作说明使用现有中文名称辅助定位。页面用户内容统一使用下列英文材料，使画面和讲解一致。
- 普通窗口登录演示买家；无痕窗口登录管理员。提前登录，录制从已登录首页开始。账户密码和支付宝支付密码不录入成片。
- 主录屏建议 1920×1080、30 fps；网页文字须可读。手机段使用开发者工具设备视口 **390×844**，外层视频仍保持横屏。这是录制建议，不是课程硬性格式。
- 切换角色时在画面左上角标 `User` / `Administrator`；代码、CI、已完成交易分别标 `Implementation` / `Test evidence` / `Earlier sandbox acceptance`。
- 鼠标移动用于指出关键字段，点完按钮后停 1–2 秒让结果可读。请求等待可剪短，但保持前后同一对象和状态，不把其他对象的结果接成实时操作。

### 画面组织方式

每个编号是一个镜头段，段内可有 2–3 个画面切换。以“页面全景交代位置 → 局部突出操作 → 保留结果反馈”为基本节奏。代码画面先出现文件／函数定位，再放大相关几行；不要在讲解时连续滚动找位置。

人物姓名和职责只在首次出场显示约 4 秒；角色、证据类型用简短角标。字幕放在不遮挡按钮、错误提示和状态的位置。手机段保留完整窄屏视口，周围空白可放一行设计解释，不将手机画面横向拉伸。长句字幕可拆成两行，避免用整段英文覆盖网页。

### 演示材料

| 材料 | 统一内容 | 用途 |
|---|---|---|
| 记录 R1 | 标题 `First Day by the Sea`；正文 `We arrived at the coast and watched the sunset together.`；日精度 `2026-11-01`；一张风景照 | 新建、草稿、恢复、保存，随后选入回忆录 |
| 记录 R2 | 标题 `An Autumn Walk`；正文 `A quiet walk reminded me why ordinary moments matter.`；月精度 `2026-10`；一张风景照 | 提前准备，展示粗日期与第二章 |
| 记录 R3 | 标题 `A Private Note`；合成正文，不含个人资料 | 提前准备，不选入回忆录，说明授权范围 |
| 回忆录 M1 | 标题 `Moments Worth Keeping`；主题 `Small moments from a meaningful journey.`；选 R1、R2 及各自一张照片 | 贯穿提交、退回、修订、生成和样张 |
| 修改内容 | 初始第一章标题 `Day One`；退回意见 `Please make the first chapter heading more specific.`；重提改为 `Day One: Arrival at the Coast` | 审核往返中的可见变化 |
| 商品 | 现有 ¥1.00 沙箱测试纪念牌，数量 1；定制文字 `Moments Worth Keeping - 2026` | 独立商品与待付款订单 |
| 地址 | `Sandbox Buyer`、`13800000000`、`Test Region`、`Sandbox address - no delivery` | 只作实体商品沙箱收货信息 |
| 演示订单 O1 | 在 S12 创建的 ¥1.00 沙箱订单；字幕显示同一个短 ID | 主版本在 S12–S14 展示同一订单的创建、付款和通知入账 |
| 备用证据 P1 | 已完成的 ¥1.00 沙箱 paid 订单及对应通知、入账事件 | 历史补充证据；不能替代 O1 的付款结果 |

R2、R3 在录制前准备好；R1 在镜头中操作。两章回忆录通常至少含封面与两章正文，适合展示“样张页数少于成品”的区别。具体页数以生成结果为准。另预备一份同内容的 ready 回忆录用于预演和异常恢复，使用备用时明确标注该对象，不冒充当前生成结果。

主版本需要在录制素材时完成 O1 的沙箱付款，并保存同一订单的创建页、收银台、返回页及只读交易证据。S12–S14 都标出相同的短订单 ID；交易表通过 `order_id` 关联 O1，支付宝商户单号对应 `merchant_no`，两个标识用途不同，不要求两者字符串相同。录制和付款尚需执行，本次文稿修订没有新增交易。

如果暂时不能补录同单付款，可保留 P1 的历史验收片段，使用 S14 后附的备用口播并标 `Earlier sandbox acceptance`。这可以证明之前完成过渠道验收，但不能证明镜头中新建的 O1 已付款。不要把两笔订单剪成同一笔；要加强相关任务的一致性证据，优先使用完整同单素材。

### 两条任务线如何衔接

- **回忆录线：**同一用户的 R1/R2 → 明确授权 → M1 修订 1 → 退回 → M1 修订 2 → 审核通过 → 生成 → 该修订的样张。R3 始终未选入。UI、审核与 PDF 共用这条材料链。
- **商品线：**同一网站账号的独立定制任务 → O1 → 签名收银台请求 → 该商户单号的通知／查询 → O1 的 paid 状态及一次入账。普通纪念牌不依赖 M1，也不把纪念牌付款解释为完整回忆录下载权限。
- **验证线：**用户需求／风险 → 对应设计 → 操作及实现 → 预期结果 → 已有实际结果 → 对设计的评价和证据边界。S16–S18 分别回扣前面的审核、付款和界面行为。

### 镜头总表

| 镜头 | 时间 | 主讲 | 主要画面 |
|---|---|---|---|
| S01 | 00:00–00:25 | HeSicheng | 项目与三人职责 |
| S02 | 00:25–00:55 | CongZheming | 首页、导航与界面职责 |
| S03 | 00:55–01:25 | CongZheming | 新建记录、保存草稿、恢复 |
| S04 | 01:25–01:55 | CongZheming | 断网输入保留、恢复后保存 |
| S05 | 01:55–02:35 | CongZheming | 日期精度、390px 响应式与数据同源 |
| S06 | 02:35–03:10 | HeSicheng | 需求、选材、授权提交 |
| S07 | 03:10–03:45 | HeSicheng | 管理员领取与权限边界 |
| S08 | 03:45–04:20 | HeSicheng | 退回、修改章节标题、重新提交 |
| S09 | 04:20–04:40 | HeSicheng | 审核通过、单独触发生成 |
| S10 | 04:40–05:05 | CongZheming | PDF 排版、样张和完整成品区别 |
| S11 | 05:05–05:40 | CuiChenshuo | 浏览器、API、MySQL 的连接 |
| S12 | 05:40–06:15 | CuiChenshuo | 独立商品定制与服务端订单快照 |
| S13 | 06:15–06:50 | CuiChenshuo | 支付地址、签名请求与可信状态 |
| S14 | 06:50–07:20 | CuiChenshuo | 同一订单付款结果与通知证据 |
| S15 | 07:20–07:45 | CuiChenshuo | 幂等、重复通知与库存 |
| S16 | 07:45–08:15 | HeSicheng | 审核和修订测试 |
| S17 | 08:15–08:45 | CuiChenshuo | 支付通知测试与 MySQL CI |
| S18 | 08:45–09:15 | CongZheming | 断网恢复与窄屏浏览器测试 |
| S19 | 09:15–09:35 | HeSicheng | Beta 边界与下一步 |

## S01 | 00:00-00:25 | HeSicheng | 项目与团队

**画面与操作**

1. 0–5 秒展示简洁标题卡 `Everhere / Milestone 2: Beta`，背景可使用网站首页录屏。
2. 5–15 秒列出三位姓名及已确认职责，不放大量文字。
3. 15–25 秒进入测试站首页，叠加任务线 `Record → Review → Memoir / Shop → Sandbox payment`。

**英文口播**

> Hello, we are the Everhere team. I am HeSicheng, responsible for requirements and memoir review design. CuiChenshuo led server and data integration; CongZheming led responsive interfaces and output layout. Everhere helps users turn private memories into reviewed memoirs and personalise keepsakes through one website.

**中文释义**

大家好，我们是 Everhere 团队。我是 HeSicheng，负责需求与回忆录审核设计。CuiChenshuo 主导服务器与数据集成，CongZheming 主导响应式界面与输出排版。Everhere 帮助用户在同一网站把私人记忆整理为经审核制作的回忆录，并定制纪念品。

**画面证据与剪辑**

标题卡仅作开场，随后立即进入实际网站。三人职责字幕与口播一致。片头音乐如果使用，应在口播开始前降低音量。

## S02 | 00:25-00:55 | CongZheming | 界面组织

**画面与操作**

1. 保持普通用户会话；显示首页和桌面侧边导航。
2. 鼠标依次指向记录、回忆录与商城入口，不逐个点开所有页面。
3. 指向新建记录入口，S03 再打开并创建，避免同一操作重复演示。

**英文口播**

> I am CongZheming. My contribution focused on responsive interfaces and output layout. I organised the screens around the user's tasks: capture a memory, organise selected material, and follow its progress. The navigation stays consistent, while each screen makes the next action and the current state visible.

**中文释义**

我是 CongZheming，我的贡献集中在响应式界面与输出排版。我围绕用户任务组织页面：记录生活、整理选定材料、跟踪处理进度。导航保持一致，每个页面则突出当前状态和下一步操作。

**画面证据与剪辑**

突出导航与当前页面，不靠快速滚动充内容。实现参考 `app/templates/index.html`、`app/templates/workspace.html` 和相应 CSS；口播强调界面职责，不把全部业务后端表述为个人工作。

## S03 | 00:55-01:25 | CongZheming | 草稿与正式记录

**画面与操作**

1. 创建已发生记录 R1，输入标题、正文、日期，上传风景照；较长输入可剪掉中间打字过程。
2. 点击“保存草稿并返回”，保留草稿保存反馈。
3. 从草稿列表继续编辑，显示标题、正文和照片仍在；此时先不正式保存。

**英文口播**

> Here I add a memory with text, a date, and a photo. I can save a draft and return to it before creating the final record. This separates unfinished input from saved memories. When I reopen the draft, the form restores the material so I can continue without entering it again.

**中文释义**

这里添加包含文字、日期和照片的记录。我可以先保存草稿，稍后再正式保存，使未完成输入与正式记录分开。再次打开草稿时，表单会恢复材料，方便继续编辑。

**画面证据与剪辑**

显示一次保存反馈及一次恢复结果。草稿在本站服务端单独保存；不要把页面中的“本机草稿”解释为已实现完整的离线浏览器数据库。

## S04 | 01:25-01:55 | CongZheming | 断网反馈与恢复

**画面与操作**

1. 在 R1 草稿正文末尾追加 `The evening light made this moment special.`。
2. 开发者工具 Network 切 Offline，点击保存，展示网络错误及仍保留的正文。
3. 切回网络可用状态，重试保存，显示正式记录详情。只在当前打开的表单中演示，不在离线状态刷新页面。

**英文口播**

> A failed request should not erase the user's work. Here the connection is interrupted, and saving reports an error while the text remains in the open form. After the connection returns, I can try again. The interface distinguishes a failed save from a successful one instead of showing a misleading success message.

**中文释义**

请求失败不应该清空用户输入。网络中断后，保存操作显示错误，但打开的表单仍保留正文。恢复连接后可以重试。界面区分保存失败与成功，避免误导用户。

**画面证据与剪辑**

错误提示与保留正文需同时可见。若网络切换耗时，剪辑操作空白，保留失败和恢复两个结果。对应证据为 `tools/product-experience-browser-check.cjs`。

## S05 | 01:55-02:35 | CongZheming | 日期与响应式

**画面与操作**

1. 在记录列表查看 R1 的日精度日期和 R2 的月精度日期。
2. 展示同一记录在时间轴／日历的引用，强调没有另建一份内容。
3. 切 390×844 视口，展示导航、记录卡片、详情和一个表单；上下滚动一次即可。
4. 恢复桌面视口，为下一段回忆录选材准备。

**英文口播**

> The same record feeds each view, preserving its ID and date precision. A month-only memory is not given an invented day. For small screens, CSS media queries change the navigation and column layout while the same data and actions remain available. I chose this approach so users can continue the same task across screen sizes without creating separate records.

**中文释义**

不同视图使用同一条记录，保留 ID 和日期精度，只知道月份的记录不会被编造日期。小屏幕下 CSS 媒体查询调整导航和列布局，数据与操作仍保持可用，使用户能跨屏幕尺寸继续同一任务，无需另建记录。

**画面证据与剪辑**

字幕可标 `One record, multiple views`、`390 × 844`。只按实际页面展示日历中的记录；月精度记录不必强行落到某个日历格。短暂指向 `app/static/css/native.css` 的窄屏导航规则，或在对应工作台页面指向 `workspace.css` 的 `.split` 单列规则，页面与代码匹配。无横向溢出由后面的浏览器测试说明。

## S06 | 02:35-03:10 | HeSicheng | 选材与明确授权

**画面与操作**

1. 用户进入回忆录，点击“整理新回忆录”，填写 M1 标题与主题。
2. 只选择 R1、R2 和勾选照片，R3 留在未选择区域。第一章标题设为 `Day One`。
3. 保存草稿，停在分享范围说明及授权复选框；勾选后提交，显示待审核。

**英文口播**

> My review design starts with a privacy requirement: users choose what a production administrator may see. Here I select two records and specific photos for a memoir. The other record remains outside this submission. Saving a draft and authorising a submission are separate steps, so the user can check the sharing scope before sending it for review.

**中文释义**

我的审核设计从隐私需求出发：用户决定制作管理员可以查看什么。这里选入两条记录和指定照片，另一条记录不在本次提交范围内。保存草稿与授权提交分开，让用户先检查共享范围，再送审。

**画面证据与剪辑**

授权范围说明至少停留两秒。实现参考 `app/services/memoirs.py::freeze` 和 `app/static/js/workspace.js::renderEditor`。画面不能把未选记录的私人内容展开给管理员。

## S07 | 03:10-03:45 | HeSicheng | 任务领取与冻结修订

**画面与操作**

1. 切到标注 `Administrator` 的已登录窗口，进入回忆录审核队列。
2. 点击领取任务，再展示本次提交的冻结章节与勾选照片。
3. 切代码或简明流程标注，突出 `assigned` 和 `revision.snapshot`；不要展开无关的整份源码。

**英文口播**

> The administrator claims this submitted revision. The server records the reviewer ID and checks it on later review requests. I chose assignment to make responsibility clear and limit access to authorised material. The frozen snapshot keeps the selected text and photos stable, so album edits cannot silently change the production input. This protects consent and consistency across the workflow.

**中文释义**

管理员领取这次提交的修订，服务器记录审核员 ID，并在后续审核请求中检查。我选择分配机制来明确责任和限制授权范围。冻结快照保留选定文字和照片，使相册后续编辑不会悄悄改变制作输入，从而保护授权与流程一致性。

**画面证据与剪辑**

实现参考 `app/services/memoirs.py::assigned`、`freeze` 和 `app/api/memoirs.py::claim`。领取前后的权限差异可用测试证据说明，不需要在这一段增加另一位管理员的登录等待。

## S08 | 03:45-04:20 | HeSicheng | 退回与重新提交

**画面与操作**

1. 管理员填写既定退回意见，点击退回，展示状态及原因。
2. 切用户窗口，打开退回稿，修改第一章标题为 `Day One: Arrival at the Coast`。
3. 保存并重新授权提交，展示提交版本从 1 到 2。正文仍来自原记录，不演示不存在的独立正文编辑器。

**英文口播**

> If a memoir needs changes, the administrator returns it with a reason. The user then updates the draft and submits a new revision. I kept these responsibilities separate: the administrator explains the problem, while the user controls the material. Keeping revisions also means an old review decision cannot be applied to a newer submission.

**中文释义**

需要修改时，管理员填写原因并退回；用户修改草稿后提交新修订。我将责任分开：管理员说明问题，用户控制材料。保留修订也意味着旧的审核决定不能直接应用到新的提交。

**画面证据与剪辑**

必须能看清退回原因、标题变化和新版本号。修改正文需要回原记录后明确更新材料版本；默认录制只修改章节标题，节省时间且与当前界面一致。

## S09 | 04:20-04:40 | HeSicheng | 审核与生成状态

**画面与操作**

1. 管理员刷新队列，领取新修订并审核通过。
2. 显示待制作状态，再点击“生成回忆录”。
3. 保留任务进度和最终 ready 状态，生成等待可压缩并标注实际等待已缩短。

**英文口播**

> Approval and generation are separate actions in this Beta. After approval, the administrator starts production. The interface reports progress and shows ready only after generation succeeds, keeping review and production status clear.

**中文释义**

本次 Beta 中审核与生成是两个操作。审核通过后，管理员启动生成任务。界面反馈进度，并在制作成功后显示成品就绪，让审核状态和制作状态容易理解。

**画面证据与剪辑**

不要说“通过审核后自动生成”。对应实现为 `app/api/memoirs.py::generate` 和 `app/services/memoir_jobs.py::run_job`。若本次生成失败，保留实际错误，另录重试或明确切换备用示例。

## S10 | 04:40-05:05 | CongZheming | PDF 输出与样张

**画面与操作**

1. 用户打开当前 ready 回忆录的样张预览，展示封面、章节、正文及照片。
2. 放大页码和样张标记。若成品页数需要说明，使用已核对的测试输出或只读页数结果，画面标 `Output verification`。
3. 短暂显示排版函数中的字号、图片等比例缩放和 `sample_pdf` 页面选择。

**英文口播**

> I chose a fixed PDF layout for consistent chapters and readable photos. The renderer takes the approved snapshot and scales each image proportionally into the page area. A separate sample copies fewer pages than the complete memoir. This keeps preview output consistent with the reviewed material.

**中文释义**

我选择固定 PDF 版式来保持章节一致和照片可读。渲染器读取已批准的快照，按比例把照片缩放到页面区域；独立样张只复制少于完整成品的页数，使预览输出与审核材料保持一致。

**画面证据与剪辑**

对应 `app/services/memoir_pdf.py::render_pdf`、`sample_pdf`。样张最多两页且至少省略成品一页；短成品可能只展示封面。此段不声称完整 PDF 已做本次实付下载验收，也不在公开样张地址打开完整文件。

## S11 | 05:05-05:40 | CuiChenshuo | 服务端与数据连接

**画面与操作**

1. 展示简图 `Browser → Flask API → MySQL`，下方补 `Alipay sandbox → Verified notification → Order state`。
2. 开发者工具 Network 展示 R1 的实际记录读取响应，指出 URL、状态码和返回的记录 ID；隐藏 Cookie 和令牌。
3. 切到 M1 冻结材料中对应的 `recordId`，显示其与 R1 ID 相同，再指向 API／模型中的归属检查。区分记录 ID、稿件 ID 和修订 ID，各自用途不同。

**英文口播**

> I am CuiChenshuo, and I led server and data integration. This API response carries the same record ID used by the memoir snapshot. Flask checks ownership before MySQL stores the state. That connects CongZheming's input screen to HeSicheng's review workflow. Server checks are necessary because a request can be sent directly, without using the visible controls.

**中文释义**

我是 CuiChenshuo，负责服务器与数据集成。API 响应里的记录 ID 与回忆录快照使用的来源记录 ID 相同，Flask 检查归属后再将状态存入 MySQL，把 CongZheming 的输入界面与 HeSicheng 的审核流程连接起来。请求可以绕过界面直接发送，因此必须进行服务器检查。

**画面证据与剪辑**

对应 `app/security.py`、`app/api/memoirs.py` 及模型。请求页面使用普通演示数据，只展示解释所需的响应字段。无需展示 `.env`、连接口令或服务器终端历史。

## S12 | 05:40-06:15 | CuiChenshuo | 商品与订单快照

**画面与操作**

1. 回到用户商城，打开 ¥1 纪念牌，选择规格并填既定定制文字，数量 1。
2. 创建待支付订单，停在商品名称、文字、数量、单价与总价。
3. 显示 `create_order` 中服务端计价和 `ShopOrderItem` 快照的相关几行。

**英文口播**

> The same user can also customise a keepsake without creating a memoir. For this order, the server checks product versions, calculates the price, and freezes the selected options. I chose a snapshot because later catalogue changes must not rewrite an agreed purchase. We now follow this same order from creation to confirmed payment.

**中文释义**

同一用户也可以独立定制纪念品，不要求先创建回忆录。服务器检查商品版本、计算价格并冻结选项；订单快照保证目录后续变化不会改写已确认的购买。接下来跟踪这同一笔订单从创建到确认付款的过程。

**画面证据与剪辑**

对应 `app/api/shop.py::create_order`。本段订单记为 O1，保存其 ID、金额、定制文字及后续商户单号，S13、S14 使用同一笔订单。若只能使用历史 P1，最后一句改为 `An earlier sandbox acceptance separately verifies the payment connection.`，并采用 S14 的备用口播。

## S13 | 06:15-06:50 | CuiChenshuo | 支付请求与可信结果

**画面与操作**

1. 展示 O1 的收货地址和付款按钮，填入合成地址，点击进入沙箱收银台；保留金额及商户单号的对应关系。
2. 使用同一订单的真实付款素材，密码输入和长等待剪去。可在代码画面播放口播，减少无信息等待；不要展示带签名参数的完整收银台 URL。
3. 切 `commerce.receive`，高亮先验签、后核对交易上下文的顺序。O1 的返回和入账结果放在 S14。

**英文口播**

> Here I start sandbox checkout for the same order. Physical items require an address. The signed request uses the stored amount and merchant reference. Because a browser redirect can be forged or interrupted, the server accepts payment only after verifying a notification or query response and checking the application, seller, order, and amount.

**中文释义**

这里为同一订单启动沙箱付款，实体商品需要地址。签名请求使用保存的金额和商户引用。由于浏览器跳回可能被伪造或中断，服务器仅在验签并核对应用、商家、订单和金额后，才接受通知或查询响应作为付款确认。

**画面证据与剪辑**

对应 `app/services/alipay.py::checkout_url`、`verify_notice`，以及 `app/services/commerce.py::receive`、`query_trade`。登录和付款使用沙箱买家账号，口播与同一订单的画面对应。若无法补录，只保留地址与代码解释，并在备用口播中明确历史验收属于另一笔订单。

## S14 | 06:50-07:20 | CuiChenshuo | 同一订单付款结果与通知证据

**画面与操作**

1. 从 O1 收银台返回 O1 详情，保留同一短订单 ID、¥1.00 和沙箱标记。
2. 展示 O1 已付款状态和付款事件时间线；在数据库结果中以 `order_id` 找到同一订单，并展示其 `merchant_no` 与交易证据相符。
3. 展示这笔订单的 `checkout`、`alipay_notice`、`paid` 事件。若在录制前已完成流程，可按原始顺序使用同一订单的预录素材，标明相关片段已预录。

**英文口播**

> We return to the same order, now marked paid for one yuan. Its merchant reference matches the transaction record, and the event list contains the verified Alipay notification and paid event. This connects the checkout request to the stored result. The page, database, and payment evidence now describe the same transaction.

**中文释义**

回到同一笔订单，它现已标为一元已付款。商户引用与交易记录一致，事件列表包含已验证的支付宝通知和入账事件，把收银台请求与保存结果连接起来。页面、数据库和支付证据现在对应同一笔交易。

**画面证据与剪辑**

新版 O1 同单付款素材尚待录制，不能用已有 P1 的结果证明 O1 入账。已有 P1 证据为一笔 ¥1.00 paid 交易，`checkout`、`alipay_notice`、`paid` 各一条，库存 12→11；该库存变化只描述验收当时。不要把当前全库事件总数当成这笔订单的事件数。

**备用口播：仅在使用历史 P1 时替换本段，不与主版本连读**

This is an earlier completed sandbox acceptance order. It separately verifies a one-yuan payment, a verified notification, and a paid event. It demonstrates the external connection, but it is not the newly created order shown earlier. The new order still needs its own payment confirmation.

备用片段必须标 `Earlier sandbox acceptance`，S12 的结尾同步改为历史证据表述，S13 不声称录下了 O1 的真实付款。两种剪辑版本择一，不混用。

历史方案中，S13 整段改读以下解释性口播：

Physical orders require an address before checkout. A signed request uses the stored amount and merchant reference. A browser redirect alone cannot confirm payment. The server verifies a notification or query response and checks the application, seller, order, and amount. The next clip shows a separate earlier sandbox acceptance.

## S15 | 07:20-07:45 | CuiChenshuo | 幂等设计

**画面与操作**

1. 显示订单创建中的请求编号与已有请求检查。
2. 显示通知事件键、唯一约束或 `event` 去重判断。
3. 简短字幕 `Retry ≠ another order / Repeated notice ≠ another paid event`。

**英文口播**

> Web requests may repeat after a timeout. I used stable request keys and recorded events to connect retries to the original operation. Repeating that request does not create another order or paid event. The tests check this beyond the successful path.

**中文释义**

请求超时后可能被重试。我将稳定请求编号和已记录事件用于把重试关联回原操作，使相同请求重复执行时不再创建另一笔订单或重复入账。测试覆盖正常成功流程之外的这种情况。

**画面证据与剪辑**

对应 `app/api/shop.py::create_order`、`app/services/commerce.py::event`、`app/models_trade.py::TradeEvent`。不要在这一段临时对实际订单连续发起付款；用明确的自动化断言展示重复操作效果。

## S16 | 07:45-08:15 | HeSicheng | 审核测试的目的与结果

**画面与操作**

1. 打开 `tests/test_workflows.py` 的双角色回忆录测试。
2. 只高亮三组断言：未授权访问、旧快照保持、旧审核版本返回 409。
3. 配合同一版本的通过结果或已验证 CI，字幕 `Expected → Observed → Meaning`。

**英文口播**

> I test across role and revision changes because permissions can fail at those boundaries. The expected outcomes are rejected unauthorised access, an unchanged earlier snapshot, and rejection of an outdated review decision. The assertions pass. This supports the design choice to freeze submissions and check the active revision before accepting a decision.

**中文释义**

测试跨角色和修订变化，因为权限容易在这些边界出问题。预期未授权访问被拒绝、旧快照不变、过期决定被拒绝；断言通过，支持冻结提交和接受决定前检查当前修订的设计。

**画面证据与剪辑**

测试：`test_two_roles_return_resubmit_generate_and_keep_immutable_selected_material`。讲述自己负责的需求与测试关注点，不将整个测试实现描述成个人独立编写。若展示历史 CI，应标注提交与运行日期。

## S17 | 08:15-08:45 | CuiChenshuo | 支付测试与结果解释

**画面与操作**

1. 打开支付宝交易测试，依次高亮错误金额被拒绝、重复通知和 paid 事件数等于 1。
2. 最后 5–8 秒显示已确认的 MySQL CI 成功结果；当前已核对的是 `017b932` 的运行。
3. 字幕明确区分 `Synthetic signed gateway test` 与 `Sandbox acceptance`。

**英文口播**

> Payment notifications may be repeated or inconsistent, so my strategy tests both conditions. A wrong amount must be rejected; repeating a valid notice must leave one paid event. Both assertions pass in MySQL. This supports signature and context checks plus event deduplication. The separate sandbox run checks the real channel connection.

**中文释义**

支付通知可能重复或不一致，因此测试这两种条件。预期错误金额被拒绝、重复有效通知只保留一次入账，两项断言在 MySQL 中通过，支持验签、交易上下文核对和事件去重的设计；独立沙箱流程验证真实渠道连接。

**画面证据与剪辑**

测试：`tests/test_alipay_commerce.py::test_physical_checkout_callback_idempotency_and_fulfillment`。已核对套件为 142 通过、0 跳过；视频中的数量以实际展示那次结果为准。参考 [017b932 CI](https://github.com/Colin-SE/EverHere-web/actions/runs/46098234584)。

## S18 | 08:45-09:15 | CongZheming | 浏览器测试与恢复

**画面与操作**

1. 显示 `tools/product-experience-browser-check.cjs` 中断网、正文保留、恢复保存的相关检查。
2. 显示通过输出与 390px 页面截图，框出无横向溢出检查。
3. 只选有通过证据的那次结果，不展示早期失败截图作为最终结果。

**英文口播**

> I test interrupted saves because a failed request could otherwise lose input, and narrow screens because overflow can hide controls. The browser checks retain the text, save after recovery, and report no horizontal overflow at 390 pixels. These results support keeping the form during failure and adapting the layout, within these tested conditions.

**中文释义**

测试中断保存，是因为请求失败可能导致输入丢失；测试窄屏，是因为溢出可能隐藏控件。浏览器检查中正文保留、恢复后保存成功，390 像素下无横向溢出；这些结果在所测条件下支持保留表单和适配布局的设计。

**画面证据与剪辑**

当前已有通过输出位于忽略的 `tmp/mysql-extra-verification.log`；截图在 `test-results/`。正式录制前核对输出与所展示代码对应。测试工具和实际网页都显示，但不为拍视频在真实业务库运行清表套件。

## S19 | 09:15-09:35 | HeSicheng | 当前边界与结束

**画面与操作**

1. 回到网站，展示记录、ready 回忆录和沙箱 paid 订单的三个短画面。
2. 简洁结束卡：`Working Beta / Reviewed memoirs / Verified sandbox payment`。
3. 留约 1 秒静止后结束，不增加长片尾。

**英文口播**

> Our Beta connects private records, reviewed memoir production, and verified sandbox payment. Some cancellation rules and further delivery checks remain future work. Each part contributes to a consistent user journey. Thank you for watching.

**中文释义**

我们的 Beta 已连接私人记录、审核制作和经过验证的沙箱付款。部分取消规则和进一步交付检查仍待完成，各部分共同组成连贯的用户任务。感谢观看。

**画面证据与剪辑**

不添加“所有功能均已完成”或“可真实付款发货”等字幕。最终交付只需一个不超过 10 分钟的 MP4；教师仓库访问和具体提交截止时间仍需按课程平台确认。

## 录制与剪辑执行说明

### 分开录素材与配音

1. 按 S01–S19 各自录一段，不要求一次读完整片。每段开头留 1 秒、结尾留 1 秒，便于对齐。
2. 先预演并录画面，再按对应英文段录音。鼠标操作与讲解可以同时进行，无需等口播结束才点按钮。
3. 三人使用相近音量和麦克风距离。交接处使用同一画面或明确的角色字幕，不靠复杂转场。
4. 录制前准备好代码标签页、CI 页面、订单证据页。打字、登录和等待可以剪短，保留输入、操作和结果之间的真实关系。
5. 每段可在段内分句剪辑，避免把说错的句子连带整段重录。中文释义用于理解，不需在视频中再念一遍。

### 语速和删减顺序

英文稿适合约 110–125 词/分钟的清楚语速。按真实录音检查每段，不因稿件词数达标就判定视频已符合时长。若某段超过时码，优先减少停顿、重复截图和无操作等待；仍超时则使用下列删减，不删除任何成员的姓名、个人贡献、设计理由或测试结果解释。

- S05 可删 `A month-only memory is not given an invented day.`，日期精度仍在首句和画面中体现。
- S07 可删 `This protects consent and consistency across the workflow.`，保留前面的审核员检查和快照机制。
- S12–S14 保留同一订单的衔接句；优先压缩输入和无信息等待，不删除证明前后对应的画面。
- S15 可删 `The tests check this beyond the successful path.`，但保留稳定请求编号和事件去重说明。
- S19 可删 `Each part contributes to a consistent user journey.`

收银台素材安排在 S13、S14 内，不在原稿后再增加一整段；保留验签和同单确认的解释。收银台登录、密码输入及长等待可以剪去，不能剪掉证明订单对应关系的画面。最终必须实际核对导出 MP4 的时长。

### 常用词读法提示

| 词 | 口述建议 |
|---|---|
| Everhere | 团队统一读法，可用 “Ever-here” |
| memoir | 近似 “MEM-wahr” |
| revision | 近似 “ri-VI-zhun” |
| snapshot | 近似 “SNAP-shot” |
| responsive | 近似 “ri-SPON-siv” |
| MySQL | 可读 “My S Q L” |
| API / PDF / CI | 按字母读 |
| Alipay | 可读 “Ali-pay” |
| idempotency | 正文使用重复请求的直白解释，无需强行读此术语 |

## 取证操作与代码定位

### 只读付款证据

可通过已有受控数据库连接查看下列字段。主版本用 O1 的实际订单 ID；历史备用版本才用 P1。只展示所选订单的结果，不把数据库连接口令、SSH 凭据或其他订单资料录入画面。此 SQL 只有 SELECT 和本次连接变量赋值，不修改订单。

```sql
SET @demo_order_id = '替换为已完成的沙箱验收订单 UUID';

SELECT o.id, o.state, t.merchant_no, t.provider_no,
       t.environment, t.amount_cents,
       t.paid_at, t.refund_state, t.fulfillment
FROM shop_orders AS o
JOIN shop_order_trades AS t ON t.order_id = o.id
WHERE o.id = @demo_order_id;

SELECT kind, COUNT(*) AS event_count
FROM shop_trade_events
WHERE order_id = @demo_order_id
GROUP BY kind;
```

数据库中的付款审计时间按 UTC 读取时，说明与网页显示的北京时间存在时区换算，不将其误说为交易不一致。历史 P1 的审计为 UTC 2026-11-28 02:36:29，对应北京时间 10:36:29；新版 O1 使用其自身的实际时间。

### 每人最少准备的实现证据

| 成员 | 实现／设计定位 | 测试定位 |
|---|---|---|
| HeSicheng | `app/services/memoirs.py` 的 `freeze`、`assigned`；`app/api/memoirs.py` 的审核和生成状态 | `tests/test_workflows.py` 的双角色退回重提测试 |
| CuiChenshuo | `app/api/shop.py::create_order`；`app/services/commerce.py::receive`、`event`；`app/services/alipay.py` 的验签 | `tests/test_alipay_commerce.py` 的错误金额及重复通知断言 |
| CongZheming | `app/static/js/workspace.js`、`app/static/js/app.js`；相关 CSS；`app/services/memoir_pdf.py` | `tools/product-experience-browser-check.cjs`；`tests/test_report_scope.py` 的样张页数边界测试 |

代码画面每次只突出与当前句子对应的几行。先解释功能目的和设计后果，再指代码位置，避免只逐行朗读语法。

## 个人提词稿与录制检查

- [HeSicheng 英文提词稿](milestone-2-scripts/HeSicheng.md)
- [CuiChenshuo 英文提词稿](milestone-2-scripts/CuiChenshuo.md)
- [CongZheming 英文提词稿](milestone-2-scripts/CongZheming.md)

录制结束检查：三人姓名与英语贡献均出现；主要功能实际运行并有连接；每人至少一个需求与设计关系、一个具体实现／流程依据、一个测试的预期和实际结果；历史验收素材标注清楚；所有声音可听清、网页文字可读；一个可播放 MP4，实际不超过 600 秒。两位教师的仓库访问与平台提交单独确认。
