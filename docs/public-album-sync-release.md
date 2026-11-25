# 公网与相册同步发布验收

适用于 `wyever.com` 和 `www.wyever.com`，阿里云实例 `Ubuntu-smcc`。第一批开启网站与共用账号，第二批开启相册同步。从 Web 发出的浏览器写请求和从 Android 发出的同步操作均使用原相册数据。管理员与普通用户继续使用现有角色。

## 第一批 · 公网与身份

1. 在当前云主机确认服务实际工作目录、Git 提交、Nginx 站点、证书、监听与数据库迁移位置。检查证书到期时间和两个域名，证书检查不读取私钥。用 `curl --resolve wyever.com:443:127.0.0.1 https://wyever.com/health` 检查内部链路。
2. 建立本次部署前的 MySQL 快照和配置备份。在隔离恢复库使用候选提交演练 `flask --app wsgi db upgrade` 和 `flask --app wsgi db check`。验证原账号与记录、照片的归属及数据库写入。第二批新增迁移为 `20261125_album_sync`。
3. 按服务器已有服务启动方式设置 `APP_ENV=production`、`SESSION_COOKIE_SECURE=true`、`ICP_FILING_NUMBER=京ICP备2026080924号-1` 与 `ALIPAY_MODE=disabled`。确认真实 SMTP 和独立 `IDENTITY_SECRET`。Nginx 覆写转发头且应用只监听本机时，配置 `TRUST_LOOPBACK_PROXY=true`。先在服务器内部验收 `SHARED_IDENTITY_ENABLED=true`，`ALBUM_SYNC_ENABLED=false`。使用生产测试收件箱验证验证码和找回，保留旧账号密码和角色。
4. 验收通过后，仅开放 Nginx 的公网 HTTPS 443。检查 `sudo nginx -t` 后再 reload，后端及数据库端口留在本机。验证两域名的证书、首页备案号、手机移动网络打开页面、Web 与 Android 各注册一次并能在另一端登录。再验证退出、换号、找回和会话撤销。

备份演练、原配置回滚和账号开关详见[共用账号部署与恢复](shared-identity-runbook.md)。真实收信与公网访问需要在云端验收。

## 第二批 · 双向同步

1. 第一批通过后，检查 MySQL `max_allowed_packet` 足以容纳 50 MiB 的原图写入及存储开销。启用 `ALBUM_SYNC_ENABLED=true` 并重启该应用服务。Android 测试包同时配置 `everhere.cnAuthApiBaseUrl` 与 `everhere.cnSyncApiBaseUrl` 指向 `https://wyever.com`，其旧版服务地址仍留空。
2. 同一测试账号先从 Android 新建人物和事件并附照片。Web 确认事件、关联人物和照片，改标题、日期并试加另一张照片，Android 再拉取。两端打开原图，核对内容一致。新安装的 Android 用同账号恢复。
3. Android 离线改稿，Web 先改同一条记录。恢复网络后核对冲突，测试保留两份和选择版本。删除时查看回收站并恢复，确认 ID 不变。原图未同步完时，确认网页显示等待，完成后可重新加载。用第二个测试账号验证记录、冲突和图片隔离。
4. 如需暂停同步，关闭 `ALBUM_SYNC_ENABLED`，保留相册及同步历史。账号需要独立停用时，按账号恢复手册处置。已有的同步历史追加表不执行自动降级。

### 当前兼容边界

普通相册使用当前账户的主资料空间，与网页登录后进入的空间一致。访客资料继续由用户明确选择归属。回忆录、订单和管理员数据继续走 Web 各自的接口。当前 Web 可接收既有记录 ID 及其数据字段，超出已支持范围的输入返回错误并保留在原设备。照片原图沿用 Web 可验证的 JPEG、PNG、WebP 和 50 MiB 上限。以真实试用账号和真机验收实际资料。

## 复验入口

- `tests/test_shared_identity.py` 验证合成账号的注册互登、找回、退出与会话撤销。
- `tests/test_album_sync.py` 以 Web 实际页面所用接口和 Android 同步协议在同一库联调，覆盖新增、编辑、原图、新安装、重复请求、冲突、软删除、恢复与跨账号隔离。
- 本地仅使用 SQLite 或独立名称以 `_test` 结尾的 MySQL 测试库。真实运营账号、邮箱授权码和签名密钥保留在各自设备与服务配置中。
