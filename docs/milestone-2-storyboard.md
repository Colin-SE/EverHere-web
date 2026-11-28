# Milestone 2 详细分镜与双语口播稿

版本：2026-11-28。基于 [整体规划](milestone-2-plan.md) 及当前已核对的 Beta。目标成片 **09:35**，共 **19 个镜头段**。以下时码是剪辑安排，不是已经实测的朗读时长；录音后需按真实语速微调，最终 MP4 不超过 10 分钟。

英文引文是需要朗读的正文；中文释义、操作说明、字幕和代码路径不朗读。每人独立提词稿见文末链接。三人的职责采用已确认分工，口播用“负责／主导”描述模块，不声称某个人独立编写了所有相关代码或测试。

全稿英文约 941 词。按每分钟约 110–125 词朗读，正文约需 7 分 32 秒至 8 分 33 秒，其余时间用于页面操作、结果停留和交接。朗读可以与操作同时进行，不能将全部操作时长再机械相加。

| 成员 | 英文词数（约） | 分配画面时间 | 出场镜头 |
|---|---:|---|---|
| HeSicheng | 328 | 3:20 | S01、S06–S09、S16、S19 |
| CuiChenshuo | 311 | 3:10 | S11–S15、S17 |
| CongZheming | 302 | 3:05 | S02–S05、S10、S18 |

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
| 付款证据 P1 | 已完成的 ¥1.00 沙箱 paid 订单及对应通知、入账事件 | 展示真实发生过的沙箱验收结果 |

R2、R3 在录制前准备好；R1 在镜头中操作。两章回忆录通常至少含封面与两章正文，适合展示“样张页数少于成品”的区别。具体页数以生成结果为准。另预备一份同内容的 ready 回忆录用于预演和异常恢复，使用备用时明确标注该对象，不冒充当前生成结果。

P1 是此前完成的验收证据。若它不属于当前演示买家，就展示标有 `Earlier sandbox acceptance` 的独立验收片段；不把它说成刚刚创建的订单。默认稿不要求再次付款。若重录完整付款，需使用同一笔订单的真实前后画面并重新核对通知，收银台等待仍计入成片时长。

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
| S14 | 06:50–07:20 | CuiChenshuo | 先前沙箱成功订单与通知证据 |
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

> Hello, we are the Everhere team. I am HeSicheng, and I coordinated requirements and memoir review design. CuiChenshuo led server and data integration. CongZheming led responsive interfaces and output layout. We will demonstrate how our Beta connects private memories, reviewed memoirs, and a custom shop.

**中文释义**

大家好，我们是 Everhere 团队。我是 HeSicheng，负责需求协调和回忆录审核设计。CuiChenshuo 主导服务器与数据集成，CongZheming 主导响应式界面与输出排版。我们将演示 Beta 如何连接私人记录、经审核制作的回忆录和定制商城。

**画面证据与剪辑**

标题卡仅作开场，随后立即进入实际网站。三人职责字幕与口播一致。片头音乐如果使用，应在口播开始前降低音量。

## S02 | 00:25-00:55 | CongZheming | 界面组织

**画面与操作**

1. 保持普通用户会话；显示首页和桌面侧边导航。
2. 鼠标依次指向记录、回忆录与商城入口，不逐个点开所有页面。
3. 打开新建记录入口，停在编辑表单。

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

> The same record supports different views, rather than creating a separate copy for each screen. Dates also preserve their precision: a memory known only by month is not given an invented day. At a narrow viewport, the layout adapts so controls and text remain usable. These choices connect the interface to the underlying data requirements.

**中文释义**

不同视图引用同一条记录，而不是分别复制内容。日期保留原有精度，只知道月份的记录不会被编造出某一天。在窄屏下，布局相应调整，让文字和控件仍可使用。这些选择把界面行为与数据需求联系起来。

**画面证据与剪辑**

字幕可标 `One record, multiple views`、`390 × 844`。只按实际页面展示日历中的记录；月精度记录不必强行落到某个日历格。无横向溢出由后面的浏览器测试说明。

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

> The administrator claims a review task before accessing the authorised material. I chose this assignment model to make responsibility clear and limit access to the selected revision. The submission is frozen, so later edits to the private album do not silently change what was reviewed. This connects user consent to a stable production input.

**中文释义**

管理员先领取审核任务，再访问获授权材料。我选择任务分配模式，是为了明确责任并限制对选定修订的访问。提交材料被冻结，因此相册之后的修改不会悄悄改变已审核内容，让授权对应稳定的制作输入。

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

> For the output layout, I focused on readable chapters, consistent spacing, and photos that keep their proportions. The preview is a separate sample document with fewer pages than the complete memoir. This lets users inspect the layout while preserving the boundary between a preview and full delivery.

**中文释义**

输出排版注重章节可读性、一致的间距和不变形的照片。预览是独立样张文档，页数少于完整回忆录，让用户检查版式，同时保持预览与完整交付之间的边界。

**画面证据与剪辑**

对应 `app/services/memoir_pdf.py::render_pdf`、`sample_pdf`。样张最多两页且至少省略成品一页；短成品可能只展示封面。此段不声称完整 PDF 已做本次实付下载验收，也不在公开样张地址打开完整文件。

## S11 | 05:05-05:40 | CuiChenshuo | 服务端与数据连接

**画面与操作**

1. 展示简图 `Browser → Flask API → MySQL`，下方补 `Alipay sandbox → Verified notification → Order state`。
2. 开发者工具 Network 展示一个实际记录或回忆录请求，鼠标指出 URL、状态码和返回数据中的对象 ID；隐藏 Cookie 和令牌。
3. 切到对应 API／模型，强调同一对象标识的连接。

**英文口播**

> I am CuiChenshuo, and I led server and data integration. Browser actions call Flask APIs, which validate ownership and store state in MySQL. The album, memoir revisions, and orders are connected through stable identifiers. The server checks the request again, because hiding a button in the interface is not enough to protect private data.

**中文释义**

我是 CuiChenshuo，负责服务器与数据集成。浏览器操作调用 Flask API，接口检查归属并将状态保存到 MySQL。相册、回忆录修订和订单通过稳定标识连接。服务器会再次检查请求，因为只隐藏界面按钮并不足以保护私人数据。

**画面证据与剪辑**

对应 `app/security.py`、`app/api/memoirs.py` 及模型。请求页面使用普通演示数据，只展示解释所需的响应字段。无需展示 `.env`、连接口令或服务器终端历史。

## S12 | 05:40-06:15 | CuiChenshuo | 商品与订单快照

**画面与操作**

1. 回到用户商城，打开 ¥1 纪念牌，选择规格并填既定定制文字，数量 1。
2. 创建待支付订单，停在商品名称、文字、数量、单价与总价。
3. 显示 `create_order` 中服务端计价和 `ShopOrderItem` 快照的相关几行。

**英文口播**

> The shop also supports ordinary keepsakes without requiring a memoir. When this order is created, the server checks the current product and variant versions, calculates the price, and stores the confirmed customisation. I used an order snapshot so later catalogue changes do not rewrite what the buyer agreed to purchase. The interface and stored order therefore describe the same transaction.

**中文释义**

商城支持独立纪念品，不要求先有回忆录。创建订单时，服务器检查商品和规格版本、计算价格并保存确认的定制内容。我使用订单快照，让目录之后的变化不会改写买家已经确认的购买内容，界面与保存的订单对应同一笔交易。

**画面证据与剪辑**

对应 `app/api/shop.py::create_order`。这个新订单仅用来展示创建和付款入口；后面的既有成功订单是另一份已完成证据，必须通过字幕和口播明确切换。

## S13 | 06:15-06:50 | CuiChenshuo | 支付请求与可信结果

**画面与操作**

1. 展示新订单的收货地址表单和付款按钮，填入合成地址；默认录制无需再次完成付款。
2. 切到 `Alipay.checkout_url`，指出金额、商户单号、通知地址和 RSA2 请求签名；使用代码画面，不展示带签名参数的完整个人收银台 URL。
3. 切 `commerce.receive`，高亮先验签、后核对交易上下文的顺序。

**英文口播**

> Physical orders require a delivery address before checkout. The payment request uses the stored amount and a signed merchant order reference. A browser redirect alone does not prove payment. The server verifies Alipay's signature and checks the application, seller, order, and amount before accepting a notification or a query result as confirmation.

**中文释义**

实体订单付款前需要收货地址。支付请求使用已保存的金额和带签名的商户订单引用。浏览器跳回本身不能证明付款成功。服务器验证支付宝签名，并核对应用、商家、订单和金额，再接受通知或查单结果作为确认。

**画面证据与剪辑**

对应 `app/services/alipay.py::checkout_url`、`verify_notice`，以及 `app/services/commerce.py::receive`、`query_trade`。如果改为录制实际收银台，登录和付款使用沙箱买家账号，口播与同一订单的画面对应。

## S14 | 06:50-07:20 | CuiChenshuo | 已完成付款的证据

**画面与操作**

1. 明确切入带 `Earlier sandbox acceptance` 字幕的 P1 片段。
2. 展示已付款订单 ¥1.00、沙箱标记和付款事件时间线；如本人无权访问 P1，用该订单所属会话录制单独素材。
3. 展示只读核对结果中同一订单的 `paid` 状态，以及 `checkout`、`alipay_notice`、`paid` 事件。只保留必要字段。

**英文口播**

> This is an earlier completed sandbox acceptance order. It shows a payment of one yuan, and the database records both the Alipay notification and the paid event. These results confirm that the external sandbox and our order state were connected successfully. Refunds and physical delivery are separate checks and are not claimed by this result.

**中文释义**

这是此前完成的一笔沙箱验收订单，金额一元，数据库记录了支付宝通知和付款入账事件。这些结果证明外部沙箱与本站订单状态已成功连接。退款和实际交付属于独立检查，这个结果不代表它们也已完成。

**画面证据与剪辑**

已有证据：一笔 ¥1.00 paid 交易，`checkout`、`alipay_notice`、`paid` 各一条，库存 12→11。库存变化属于这笔验收当时的核对，不要求录制当天全库仍是 12→11。不要把当前全库事件总数当成这笔订单的事件数。

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

> For my review design, our strategy focuses on excessive access and decisions applied to the wrong revision. The test follows submission, return, and resubmission. It expects unauthorised access to fail, the earlier snapshot to remain unchanged, and an outdated decision to be rejected. The passing assertions support the privacy and revision rules.

**中文释义**

审核流程的关键风险是越权访问，以及审核决定应用到错误修订。测试走过提交、退回和重提，预期未授权访问失败、旧快照不变、过期决定被拒绝。通过的断言支持前面演示的隐私和修订规则。

**画面证据与剪辑**

测试：`test_two_roles_return_resubmit_generate_and_keep_immutable_selected_material`。讲述自己负责的需求与测试关注点，不将整个测试实现描述成个人独立编写。若展示历史 CI，应标注提交与运行日期。

## S17 | 08:15-08:45 | CuiChenshuo | 支付测试与结果解释

**画面与操作**

1. 打开支付宝交易测试，依次高亮错误金额被拒绝、重复通知和 paid 事件数等于 1。
2. 最后 5–8 秒显示已确认的 MySQL CI 成功结果；当前已核对的是 `017b932` 的运行。
3. 字幕明确区分 `Synthetic signed gateway test` 与 `Sandbox acceptance`。

**英文口播**

> For my integration work, our strategy covers incorrect and repeated external messages. The test sends an incorrect amount and repeats a valid signed notification. We expect rejection of the wrong amount and only one paid event. These assertions pass in MySQL. The separate sandbox acceptance checks the external connection.

**中文释义**

支付测试发送错误金额，并重复发送有效签名通知。预期错误金额被拒绝，最终只保留一次付款入账事件。这些断言在 MySQL 测试套件中通过。受控网关测试解释失败处理，独立沙箱订单则提供外部连接证据。

**画面证据与剪辑**

测试：`tests/test_alipay_commerce.py::test_physical_checkout_callback_idempotency_and_fulfillment`。已核对套件为 142 通过、0 跳过；视频中的数量以实际展示那次结果为准。参考 [017b932 CI](https://github.com/Colin-SE/EverHere-web/actions/runs/46098234584)。

## S18 | 08:45-09:15 | CongZheming | 浏览器测试与恢复

**画面与操作**

1. 显示 `tools/product-experience-browser-check.cjs` 中断网、正文保留、恢复保存的相关检查。
2. 显示通过输出与 390px 页面截图，框出无横向溢出检查。
3. 只选有通过证据的那次结果，不展示早期失败截图作为最终结果。

**英文口播**

> For my interface work, our strategy covers interrupted editing and narrow screens because these affect everyday use. The browser checks expect text to remain during a failed save, saving to succeed after recovery, and no horizontal overflow at 390 pixels. The passing results support the feedback and layout decisions shown earlier.

**中文释义**

界面浏览器检查会在编辑中断网再恢复，预期文字仍保留、恢复后保存成功；同时检查窄屏是否横向溢出。观察结果支持可用的恢复和响应式布局，而不只是证明页面能够打开。

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

- S05 可删 `These choices connect the interface to the underlying data requirements.`
- S07 可删 `This connects user consent to a stable production input.`
- S12 可删 `The interface and stored order therefore describe the same transaction.`
- S15 可删 `The tests check this beyond the successful path.`，但保留稳定请求编号和事件去重说明。
- S19 可删 `Each part contributes to a consistent user journey.`

如果现场需要额外展示收银台，不在原稿后再增加一整段；使用 S13、S14 的时间替换相应素材，保留验签与确认结果的解释。最终必须实际核对导出 MP4 的时长。

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

可通过已有受控数据库连接查看下列字段。用实际 P1 订单 ID 替换占位内容，并只展示该订单的结果；不要把数据库连接口令、SSH 凭据或其他订单资料录入画面。此 SQL 只有 SELECT 和本次连接变量赋值，不修改订单。

```sql
SET @demo_order_id = '替换为已完成的沙箱验收订单 UUID';

SELECT o.id, o.state, t.environment, t.amount_cents,
       t.paid_at, t.refund_state, t.fulfillment
FROM shop_orders AS o
JOIN shop_order_trades AS t ON t.order_id = o.id
WHERE o.id = @demo_order_id;

SELECT kind, COUNT(*) AS event_count
FROM shop_trade_events
WHERE order_id = @demo_order_id
GROUP BY kind;
```

数据库中的付款审计时间按 UTC 读取时，说明与网页显示的北京时间存在时区换算，不将其误说为交易不一致。现有该笔支付审计为 UTC 2026-11-28 02:36:29，对应北京时间 10:36:29。

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
