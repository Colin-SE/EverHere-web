# 共用身份接口契约

2026-11-14，本地实现。仅中国区。服务基础地址是独立 origin。

## Android

前缀 `/v1/auth`。所有请求必须带 `X-Everhere-Region: cn`；需要身份的请求另带 `Authorization: Bearer <accessToken>`。不使用 Cookie / CSRF。请求 JSON 最大16KiB；响应 Cache-Control=no-store。成功直接返回对象；错误为 `{"error":"invalid_code"}` 等小写协议码，不是 Web 的 error 对象。缺配置503、跨区400、凭证无效401、限流429、服务暂不可用503。

| 方法/路径 | 输入 | 成功结果 |
|---|---|---|
| POST /code | email、purpose=register/reset | challengeId(UUID)、expiresInSeconds=600 |
| POST /register | challengeId、code(8位)、password(12—128) | 201；userId、email、region=cn；不自动登录 |
| POST /login | email、password(兼容旧密码)、installationId(UUID)、deviceName(1—80) | SessionTokens |
| POST /refresh | refreshToken、installationId、operationId(UUID) | SessionTokens，userId/sessionId保持 |
| GET /me | Bearer | userId、sessionId、email、region=cn |
| GET /sessions | Bearer | sessions数组；每项sessionId/deviceName/createdAt/expiresAt/current |
| POST /logout | Bearer | revoked=true，仅当前手机会话 |
| POST /logout-all | Bearer | revoked=true，全部手机与浏览器会话失效 |
| POST /revoke-session | Bearer、sessionId | revoked=true；只能撤销自己的会话，未知/他人ID不泄漏存在性 |
| POST /reset-password | challengeId、code、password | reset=true，全部会话撤销；不自动登录 |
| POST /change-password | Bearer、oldPassword、newPassword | changed=true，全部会话撤销 |
| POST /delete-account、/deletion-status、/deletion-ack | 暂不可用 | 503 temporarily_unavailable；不返回删除成功 |

SessionTokens 字段：region=`cn`，userId/sessionId为规范小写UUID，email，accessToken/refreshToken为43位 `[A-Za-z0-9_-]` 随机字符串，accessExpiresAt/refreshExpiresAt为带Z的UTC ISO时间。刷新遇到不确定网络结果，必须保留旧 token 与同一 operationId 重试；另一次刷新使用新 operationId。installationId 只绑定设备，不作为资料所有者。

常见协议错误：invalid_email、invalid_id、invalid_device、invalid_purpose、password_length、invalid_credentials、invalid_code、account_exists、unauthorized、session_revoked、rotation_id_reused、region_mismatch、request_too_large、try_later、mail_unavailable、service_not_configured、temporarily_unavailable。密码或验证码不通过 URL 发送；请求体和 Authorization 不入日志。

不注册 `/v1/sync` 或 `/v1/assets`，也不允许 Bearer 访问 Web 原相册/管理员接口。记录/照片的统一授权与映射属于第二批。

## Web

沿用 `/api/v1`、Cookie和写请求 `X-CSRF-Token`。先 GET `/auth/session` 获得 CSRF，完成后再读 capabilities；不能并发创建两个初始 Cookie。成功为 `{data:...}`，失败为 `{error:{code,message}}`。

| 路径 | 行为 |
|---|---|
| GET /accounts/capabilities | sharedIdentity布尔值、region=cn；网页据此显示验证码与找回入口 |
| POST /accounts/code | 与手机同一邮件挑战服务；email/purpose；返回challengeId/expiresInSeconds |
| POST /accounts/register | 原name/email/password/claimCurrentSpace；启用时增加challengeId/code，验证码邮箱必须与提交邮箱一致；返回原member/csrfToken并建立浏览器会话 |
| POST /accounts/login | 原email/password，保留原member角色与CSRF响应；与找回并发时复验密码版本 |
| POST /accounts/reset-password | email/challengeId/code/password；验证码邮箱必须匹配；reset=true，随后用户用新密码登录 |
| POST /accounts/logout | 原浏览器退出及未认领游客空间返回规则保持 |

验证码错误、过期、发送失败和网络失败不重绘/清空表单；重发成功后替换当前内存挑战编号。邮箱改变后必须为新地址重新取码。密码不保存到 localStorage、URL或日志；页面关闭后的密码不持久化恢复。
