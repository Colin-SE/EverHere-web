# CuiChenshuo 英文提词稿

职责：服务器与数据集成。版本：2026-11-28。

本稿按成片出场顺序排列。只朗读每段英文正文，不读标题、时码和画面提示。合计约 **305 个英文词**，分配画面时间 **3:10**；其中包含操作与结果展示。时间为计划，不是已录制时长。

完整操作、中文释义和证据要求见 [详细分镜](../milestone-2-storyboard.md)。三人的职责按团队已确认分工表述；录制前核对个人实际参与内容。

**付款素材版本：**以下 S12–S14 是同一 O1 的完整付款主版本，尚需实际录制对应素材。若只使用此前 P1，请按详细分镜替换 S12 结尾、S13 全段及 S14 全段，不用历史 P1 的结果配新 O1 的口播。备用稿不重复计入本稿词数。

## S11 | 05:05–05:40 | 服务端与数据连接

画面提示：服务端与数据连接。预计 35 秒，约 56 词。

I am CuiChenshuo, and I led server and data integration. This API response carries the same record ID used by the memoir snapshot. Flask checks ownership before MySQL stores the state. That connects CongZheming's input screen to HeSicheng's review workflow. Server checks are necessary because a request can be sent directly, without using the visible controls.

## S12 | 05:40–06:15 | 商品与订单快照

画面提示：商品与订单快照。预计 35 秒，约 53 词。

The same user can also customise a keepsake without creating a memoir. For this order, the server checks product versions, calculates the price, and freezes the selected options. I chose a snapshot because later catalogue changes must not rewrite an agreed purchase. We now follow this same order from creation to confirmed payment.

## S13 | 06:15–06:50 | 支付请求与可信结果

画面提示：支付请求与可信结果。预计 35 秒，约 53 词。

Here I start sandbox checkout for the same order. Physical items require an address. The signed request uses the stored amount and merchant reference. Because a browser redirect can be forged or interrupted, the server accepts payment only after verifying a notification or query response and checking the application, seller, order, and amount.

## S14 | 06:50–07:20 | 同一订单付款结果与通知证据

画面提示：同一订单付款结果与通知证据。预计 30 秒，约 51 词。

We return to the same order, now marked paid for one yuan. Its merchant reference matches the transaction record, and the event list contains the verified Alipay notification and paid event. This connects the checkout request to the stored result. The page, database, and payment evidence now describe the same transaction.

## S15 | 07:20–07:45 | 幂等设计

画面提示：幂等设计。预计 25 秒，约 41 词。

Web requests may repeat after a timeout. I used stable request keys and recorded events to connect retries to the original operation. Repeating that request does not create another order or paid event. The tests check this beyond the successful path.

## S17 | 08:15–08:45 | 支付测试与结果解释

画面提示：支付测试与结果解释。预计 30 秒，约 51 词。

Payment notifications may be repeated or inconsistent, so my strategy tests both conditions. A wrong amount must be rejected; repeating a valid notice must leave one paid event. Both assertions pass in MySQL. This supports signature and context checks plus event deduplication. The separate sandbox run checks the real channel connection.

录音结束后回听姓名、关键词和最后一句是否清楚；按镜头编号交付音频，便于与另外两位的段落合并。
