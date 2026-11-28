# HeSicheng 英文提词稿

职责：需求协调与回忆录审核设计。版本：2026-11-28。

本稿按成片出场顺序排列。只朗读每段英文正文，不读标题、时码和画面提示。合计约 **332 个英文词**，分配画面时间 **3:20**；其中包含操作与结果展示。时间为计划，不是已录制时长。

完整操作、中文释义和证据要求见 [详细分镜](../milestone-2-storyboard.md)。三人的职责按团队已确认分工表述；录制前核对个人实际参与内容。

## S01 | 00:00–00:25 | 项目与团队

画面提示：项目与团队。预计 25 秒，约 44 词。

Hello, we are the Everhere team. I am HeSicheng, responsible for requirements and memoir review design. CuiChenshuo led server and data integration; CongZheming led responsive interfaces and output layout. Everhere helps users turn private memories into reviewed memoirs and personalise keepsakes through one website.

## S06 | 02:35–03:10 | 选材与明确授权

画面提示：选材与明确授权。预计 35 秒，约 57 词。

My review design starts with a privacy requirement: users choose what a production administrator may see. Here I select two records and specific photos for a memoir. The other record remains outside this submission. Saving a draft and authorising a submission are separate steps, so the user can check the sharing scope before sending it for review.

## S07 | 03:10–03:45 | 任务领取与冻结修订

画面提示：任务领取与冻结修订。预计 35 秒，约 59 词。

The administrator claims this submitted revision. The server records the reviewer ID and checks it on later review requests. I chose assignment to make responsibility clear and limit access to authorised material. The frozen snapshot keeps the selected text and photos stable, so album edits cannot silently change the production input. This protects consent and consistency across the workflow.

## S08 | 03:45–04:20 | 退回与重新提交

画面提示：退回与重新提交。预计 35 秒，约 54 词。

If a memoir needs changes, the administrator returns it with a reason. The user then updates the draft and submits a new revision. I kept these responsibilities separate: the administrator explains the problem, while the user controls the material. Keeping revisions also means an old review decision cannot be applied to a newer submission.

## S09 | 04:20–04:40 | 审核与生成状态

画面提示：审核与生成状态。预计 20 秒，约 32 词。

Approval and generation are separate actions in this Beta. After approval, the administrator starts production. The interface reports progress and shows ready only after generation succeeds, keeping review and production status clear.

## S16 | 07:45–08:15 | 审核测试的目的与结果

画面提示：审核测试的目的与结果。预计 30 秒，约 52 词。

I test across role and revision changes because permissions can fail at those boundaries. The expected outcomes are rejected unauthorised access, an unchanged earlier snapshot, and rejection of an outdated review decision. The assertions pass. This supports the design choice to freeze submissions and check the active revision before accepting a decision.

## S19 | 09:15–09:35 | 当前边界与结束

画面提示：当前边界与结束。预计 20 秒，约 34 词。

Our Beta connects private records, reviewed memoir production, and verified sandbox payment. Some cancellation rules and further delivery checks remain future work. Each part contributes to a consistent user journey. Thank you for watching.

录音结束后回听姓名、关键词和最后一句是否清楚；按镜头编号交付音频，便于与另外两位的段落合并。
