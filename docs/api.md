# 当前 Web API

前缀 `/api/v1`。成功 `data`，失败 `error:{code,message}`。签名Cookie选择本机空间；GET `/auth/session` 返回CSRF，变更请求带 `X-CSRF-Token`。客户端owner/userId不授予访问权。下列本机接口不调用共同云。

| 路径 | 方法 | 行为 |
|---|---|---|
| /auth/session | GET | 本机会话、csrfToken、region、共同云是否配置 |
| /records | GET | target=all/timeline/spatial；q全部词、state/progress/precision/from/to/tag/people/node，trash=true仅回收站 |
| /records | POST | 建立正式记录，正常界面通过草稿提交 |
| /records/{id} | GET / PUT / DELETE | 同ID读取/版本编辑/软删除；删除后GET404 |
| /records/{id}/restore | POST | version，恢复同ID/原图/关系 |
| /photos / /photos/batch | POST | photo/photos表单，JPEG/PNG/WebP原字节，最多10张，每张50MiB/100MP；批量失败回滚 |
| /photos/{id} | GET | 只读取当前空间原图，不缓存 |
| /graph | GET | 正式关系资料，人物UI只使用person；其他类型用于原生归档保真 |
| /graph/entities | POST | 创建人物（名称/意义），同名不合并 |
| /graph/entities/{id} | PUT / DELETE | 版本编辑/软删除人物，解绑但保留记录原图 |
| /drafts | GET / POST | 当前未提交草稿；kind=record/person，recordId/personId或values |
| /drafts/{id} | GET / PUT / DELETE | values+version保存、恢复、放弃，过期409 |
| /drafts/{id}/commit | POST | version；正式目标baseVersion冲突409；重复提交同一结果 |
| /archive/export | GET | Android普通JSON，不含原图 |
| /archive/export.zip | GET | 完整原图ZIP，缺原图409，不输出不完整包 |
| /archive/files/preview | POST | archive文件表单，原生JSON/ZIP严格校验；本机加密暂存，正式资料不写入 |
| /archive/jobs | GET | 当前空间未完成预览 |
| /archive/jobs/{id} | GET / DELETE | 继续或删除本次暂存 |
| /archive/jobs/{id}/refresh | POST | 本机变化后重新计算预览与目标指纹 |
| /archive/jobs/{id}/confirm | POST | confirmed=true；缺图acceptMissingPhotos；冲突copyConflicts；执行重验目标，24小时到期须重选 |
| /archive/preview / /archive/import | POST | 程序调用原生JSON预览/导入；archive+fingerprint+targetFingerprint及显式冲突/缺图选择 |
| /cloud/status | GET | 配置/账号/权益状态，enabled始终false |
| /cloud/login | POST | 共同email/password，只获取身份 |
| /cloud/consent | POST | 无权益/范围许可时拒绝 |
| /cloud/logout | POST | 共同云退出及清凭证，本机事实保留 |

记录字段：recordState=occurred/ongoing/planned（兼容导入recurring），completionState独立，datePrecision=day/month/year/range/unknown；eventDate/eventStartAt/eventEndAt保留精度，timezone显式；placeName/latitude/longitude/placePrecision、tags、mood、photoUris、linkedEntityIds、showInTimeline/showOnGlobe。计划改已发生且选实际日期需要actualDateConfirmed=true。PUT/删除/恢复须version，冲突不覆盖。

归档仅支持 everhere-archive/1，同区、校验和、严格schema；不接受旧schemaVersion1/2或受保护资料。单次JSON16MiB/ZIP128MiB。CRC、SHA256、图片类型/尺寸、重复路径和非清单内容校验失败整体拒绝。恢复支持保留两份的稳定复制ID；不覆盖原资料、墓碑或活动草稿。

旧本地注册/密码登录/账户删除/保险箱路由已删除，返回404。协议中保留对象/阶段/长期投入数据不代表其完整页面已实现。
