# 中国区 Android 与 Web 共用账号：第一批

更新：2026-11-14。功能 AUTH-CN-SHARED / AUTH-01。本批为本地实现与验证，未部署生产。

## 当前决定与范围

用户确认现在只运营一套中国区服务。保留国际 flavor、region 和国际配置，暂不部署国际服务；语言选择不切换服务区。先共用注册、邮箱验证、登录、找回和会话，下一批再同步文字、人物、照片及处理离线冲突/恢复。两端功能可以不同，服务端分别授权。

Web 基线为 `Colin-SE/EverHere-web` 的 `重构版`，`3a513e32cb00acf641bd1224cdf0d32488b1cd15`；2026-11-14 远端核对仍只有 `main` 与 `重构版`。Android 远端 main 为 `9c4335e27e7f8054248c422e435dcafd5b40a283`，code38 / 0.0.38-ui-finish，Room9 / PG009 / 同步1.1 / 归档2。本批未改手机版本、地址、数据库或课程仓库。

已读取 Web 交接对话“提交”的部署和备份部分。该线记载服务位于 `~/apps/everhere-web`，systemd `everhere.service`、MySQL `life_album`、本机 `127.0.0.1:5000`、Nginx 仅 `127.0.0.1:443`，域名 `wyever.com`；这些是交接记录，尚未取得远程连接重新核验精确运行 SHA。11月14日备份不是本次部署前的新备份，也未完成独立恢复演练。

文档指定的 D 盘在当前环境未挂载。实际读取到的 C 盘 Web 有既有 Dockerfile 修改和 output/，Android main 干净。本批在当前聊天 `work/web` 中建立临时隔离开发副本，未覆盖 C 盘预览、Dockerfile 或原资料；它不是第二个日常运行入口。后续整合前重新核对真正维护目录及并发工作。

## 身份选择

复用 Web `members.id` 作为中国区稳定 `userId`，继续通过 `space_ownerships` 保持原相册归属。旧邮箱、密码哈希、角色、账号 ID、记录和照片 ID 均不重编号。新账号只能成为 user；手机的 owner 输入、同邮箱、语言和 Cookie 都不授予管理员权限。

浏览器继续 Flask-Login 签名 HttpOnly Cookie + CSRF；手机继续已有 `/v1/auth`、Bearer、短期 access 和轮换 refresh 协议及 Keystore 保护的 SessionVault。手机接口不读取 Cookie、不建立访客空间；两端读取同一行 Member。Web 管理员仍由受控命令建立。旧账号未验证邮箱可继续用原密码登录；通过新注册或邮箱找回后记录 `email_verified_at`，不假称旧邮箱已验证。

选择这个方案是因为现有生产身份、相册、回忆录和商城归属已经在 MySQL。若直接换成 Fastify 的 `users/auth_accounts`，需要迁移密码哈希、所有业务外键和旧 Cookie，增加旧资料丢失风险。仅改 URL 也不能兼容两个系统的响应和凭证格式。

Fastify/PostgreSQL 的验证码、设备会话、轮换幂等与重放撤销规则作为协议参考，既有同步、冲突、私有资源和冻结迁移全部保留。第一批不另外部署 Fastify 账号库；第二批先评估把同步模块接到既有身份授权、是否保留 PG 资料服务，或受控迁移协议，使用稳定 ID 的显式映射。不能凭邮箱创建或合并另一个主体，也不将手机凭证直接用于当前未接通的同步服务。

## 生命周期与边界

- 新注册：邮件八位验证码，十分钟有效、最多五次错误、一次消费；重发撤销旧码。同邮箱请求串行，账号唯一约束保留。
- 新密码 12—128 字符；旧 Web 的 10 字符密码仍可在两端登录，沿用 Werkzeug 的原哈希验证。没有以新注册规则拒绝旧登录。
- Access 十分钟；refresh 最长三十天，不因轮换无限延长。凭证只存 SHA-256 摘要。轮换回执用独立密钥派生的 Fernet 加密，两分钟内同旧 token + installationId + operationId 重试返回同一结果；不同操作重放撤销该会话。保留完整已用 token 摘要，不能只检测上一个 token。
- 撤销、找回、修改密码与会话授权按 Member → DeviceSession 顺序加锁。找回/改密撤销全部手机会话，并增加 `auth_epoch` 使旧浏览器 Cookie 失效；旧无 epoch Cookie 只在 epoch=0 时兼容。会话建立使用锁内捕获的 epoch。
- 限流记录在 MySQL，跨 worker 有效，键为地址/IP的 HMAC，不在日志保存密码、验证码、完整凭证。全接口90次/5分钟/IP；登录15次/5分钟/邮箱；验证码每邮箱合计3次/小时，单码最多5次错误。
- SMTP 仅 TLS465 或 STARTTLS；无控制台验证码或假发送降级。测试邮件回调仅 TESTING 生效。重复注册/不存在邮箱找回返回相同挑战结构，不创建、合并或接管旧账号。
- 登录不认领游客资料。Web 新注册仅在用户主动勾选时认领当前空间；手机保留已有游客确认流程。第一批没有同步记录、原图、草稿或保险箱，也不授予付费权益。

## 配置与部署

默认 `SHARED_IDENTITY_ENABLED=false`。启用前必须先执行追加迁移 `20261114_shared_identity`、安全配置独立 IDENTITY_SECRET、核对真实 SMTP 和反向代理，再实际验收。SMTP 私人网易邮箱的具体后缀、开通能力、发送限制与授权码尚未确认；不把私人邮箱当成已配置好的生产发信服务。

API 契约见 [shared-identity-api.md](shared-identity-api.md)，服务器步骤与恢复见 [shared-identity-runbook.md](shared-identity-runbook.md)，证据见 [shared-identity-verification.md](shared-identity-verification.md)。

Android `everhere.cnApiBaseUrl` 将来填可达 HTTPS origin，例如经验证后的 `https://wyever.com`，不带 `/api` 或 `/v1`。当前保持为空；国际配置保持原样。配置前须检查账号页仍能清楚说明“账号已接通，记录与照片尚未同步”；不交付一个会误报云同步可用的包。当前注销接口明确返回503，Web 业务保留/删除规则需另行设计，不能宣传注销完成。

上线验收仍需：真实收信、双端真实注册互登、手机重启保持与退出、真实找回、普通用户/管理员隔离、旧账号与已有资料归属、服务器内部 HTTPS 和真正公网路径。备案和开放状态由实际核对决定，本批不改变公网监听或安全组。
