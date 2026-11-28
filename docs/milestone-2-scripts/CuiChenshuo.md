# CuiChenshuo 英文提词稿

职责：服务器与数据集成。版本：2026-11-28。

本稿按成片出场顺序排列。只朗读每段英文正文，不读标题、时码和画面提示。合计约 **311 个英文词**，分配画面时间 **3:10**；其中包含操作与结果展示。时间为计划，不是已录制时长。

完整操作、中文释义和证据要求见 [详细分镜](../milestone-2-storyboard.md)。三人的职责按团队已确认分工表述；录制前核对个人实际参与内容。

## S11 | 05:05–05:40 | 服务端与数据连接

画面提示：服务端与数据连接。预计 35 秒，约 54 词。

I am CuiChenshuo, and I led server and data integration. Browser actions call Flask APIs, which validate ownership and store state in MySQL. The album, memoir revisions, and orders are connected through stable identifiers. The server checks the request again, because hiding a button in the interface is not enough to protect private data.

## S12 | 05:40–06:15 | 商品与订单快照

画面提示：商品与订单快照。预计 35 秒，约 60 词。

The shop also supports ordinary keepsakes without requiring a memoir. When this order is created, the server checks the current product and variant versions, calculates the price, and stores the confirmed customisation. I used an order snapshot so later catalogue changes do not rewrite what the buyer agreed to purchase. The interface and stored order therefore describe the same transaction.

## S13 | 06:15–06:50 | 支付请求与可信结果

画面提示：支付请求与可信结果。预计 35 秒，约 52 词。

Physical orders require a delivery address before checkout. The payment request uses the stored amount and a signed merchant order reference. A browser redirect alone does not prove payment. The server verifies Alipay's signature and checks the application, seller, order, and amount before accepting a notification or a query result as confirmation.

## S14 | 06:50–07:20 | 已完成付款的证据

画面提示：已完成付款的证据。预计 30 秒，约 55 词。

This is an earlier completed sandbox acceptance order. It shows a payment of one yuan, and the database records both the Alipay notification and the paid event. These results confirm that the external sandbox and our order state were connected successfully. Refunds and physical delivery are separate checks and are not claimed by this result.

## S15 | 07:20–07:45 | 幂等设计

画面提示：幂等设计。预计 25 秒，约 41 词。

Web requests may repeat after a timeout. I used stable request keys and recorded events to connect retries to the original operation. Repeating that request does not create another order or paid event. The tests check this beyond the successful path.

## S17 | 08:15–08:45 | 支付测试与结果解释

画面提示：支付测试与结果解释。预计 30 秒，约 49 词。

For my integration work, our strategy covers incorrect and repeated external messages. The test sends an incorrect amount and repeats a valid signed notification. We expect rejection of the wrong amount and only one paid event. These assertions pass in MySQL. The separate sandbox acceptance checks the external connection.

录音结束后回听姓名、关键词和最后一句是否清楚；按镜头编号交付音频，便于与另外两位的段落合并。
