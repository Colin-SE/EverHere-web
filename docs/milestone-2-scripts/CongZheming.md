# CongZheming 英文提词稿

职责：响应式界面与输出排版。版本：2026-11-28。

本稿按成片出场顺序排列。只朗读每段英文正文，不读标题、时码和画面提示。合计约 **307 个英文词**，分配画面时间 **3:05**；其中包含操作与结果展示。时间为计划，不是已录制时长。

完整操作、中文释义和证据要求见 [详细分镜](../milestone-2-storyboard.md)。三人的职责按团队已确认分工表述；录制前核对个人实际参与内容。

## S02 | 00:25–00:55 | 界面组织

画面提示：界面组织。预计 30 秒，约 46 词。

I am CongZheming. My contribution focused on responsive interfaces and output layout. I organised the screens around the user's tasks: capture a memory, organise selected material, and follow its progress. The navigation stays consistent, while each screen makes the next action and the current state visible.

## S03 | 00:55–01:25 | 草稿与正式记录

画面提示：草稿与正式记录。预计 30 秒，约 51 词。

Here I add a memory with text, a date, and a photo. I can save a draft and return to it before creating the final record. This separates unfinished input from saved memories. When I reopen the draft, the form restores the material so I can continue without entering it again.

## S04 | 01:25–01:55 | 断网反馈与恢复

画面提示：断网反馈与恢复。预计 30 秒，约 52 词。

A failed request should not erase the user's work. Here the connection is interrupted, and saving reports an error while the text remains in the open form. After the connection returns, I can try again. The interface distinguishes a failed save from a successful one instead of showing a misleading success message.

## S05 | 01:55–02:35 | 日期与响应式

画面提示：日期与响应式。预计 40 秒，约 59 词。

The same record feeds each view, preserving its ID and date precision. A month-only memory is not given an invented day. For small screens, CSS media queries change the navigation and column layout while the same data and actions remain available. I chose this approach so users can continue the same task across screen sizes without creating separate records.

## S10 | 04:40–05:05 | PDF 输出与样张

画面提示：PDF 输出与样张。预计 25 秒，约 46 词。

I chose a fixed PDF layout for consistent chapters and readable photos. The renderer takes the approved snapshot and scales each image proportionally into the page area. A separate sample copies fewer pages than the complete memoir. This keeps preview output consistent with the reviewed material.

## S18 | 08:45–09:15 | 浏览器测试与恢复

画面提示：浏览器测试与恢复。预计 30 秒，约 53 词。

I test interrupted saves because a failed request could otherwise lose input, and narrow screens because overflow can hide controls. The browser checks retain the text, save after recovery, and report no horizontal overflow at 390 pixels. These results support keeping the form during failure and adapting the layout, within these tested conditions.

录音结束后回听姓名、关键词和最后一句是否清楚；按镜头编号交付音频，便于与另外两位的段落合并。
