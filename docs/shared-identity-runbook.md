# 共用账号部署准备与恢复

2026-11-14。本文是待审阅操作步骤，未在服务器执行；不授权改变公网入口。先以服务器实际现状替换交接假设。

## 1. 只读现状核对

通过用户已有阿里云远程终端或已配置SSH进入服务器。当前未发现本机可用的SSH配置，不索要聊天密码/私钥。连接后先只读：

```sh
cd ~/apps/everhere-web
git status --short
git rev-parse HEAD
git branch --show-current
git remote -v
sudo systemctl is-active everhere
sudo systemctl show everhere -p WorkingDirectory -p ExecStart -p User --no-pager
sudo ss -lntp
sudo nginx -t
curl --fail --silent --show-error --resolve wyever.com:443:127.0.0.1 https://wyever.com/health
```

只核对 Nginx 中的 listen/proxy_pass/转发头、systemd工作目录和启动器；不要输出 `.env`、数据库行、私钥或完整服务 Environment。确认当前迁移头、MySQL版本、剩余磁盘、数据库名和部署SHA。若 HEAD 不是已核对基线，先比较差异；有未提交修改时不覆盖。不要停止其他站点。

交接配置为 Nginx监听 `127.0.0.1:443`，代理 `127.0.0.1:5000`。备案等待期间继续保留；不修改 listen、不放行安全组、不绕过访问限制。现有 location / 已能转发 `/v1/auth/`，无需另起账号服务或开放 Fastify 端口。

## 2. 新备份与恢复准备

暂停本网站写入窗口后做本次更新前备份，使用权限0700目录、umask077，保存当前精确SHA、数据库的single-transaction/hex-blob备份、受保护.env、Nginx和systemd配置；核对命令退出码与SHA256，把独立副本下载到用户电脑。数据库内含账号、照片、PDF和商品图片；不能只备份 instance/。不读取或将备份传到GitHub。

部署前至少在隔离 `_test` 数据库恢复新备份，核对表数量、账号/空间归属的计数与外键、照片/PDF二进制摘要及可登录性（由用户输入自己的凭证）。隔离库不可对外服务、不可发送邮件；恢复验证后按用户资料处理。不要在真实库运行 pytest、db.create_all、drop_all、清库脚本或测试种子。

若无法实际恢复，明确保留该项未验收，先不做身份迁移。已有11月14日备份不能冒充本次已恢复验证的备份。

## 3. 邮件与密钥配置

`.env.example` 已列出所需字段。`IDENTITY_SECRET` 为新生成的32字节独立随机值，保存64位十六进制。SMTP host/port/TLS/user/from 根据确认的网易邮箱后缀及官方设置填写；SMTP password使用邮箱设置生成的授权码，不是邮箱网页登录密码。不在聊天、截图或Git提交中暴露，不运行会打印全部环境变量的诊断。

先保持 SHARED_IDENTITY_ENABLED=false。私有 `.env` 只允许服务账户读取；现有 SECRET_KEY 不随意改变，否则会使浏览器会话全部退出。检查网易账号是否允许SMTP、发件名/地址、TLS支持、发送额度和退信；用真实收件箱验收注册和重置各一封，包含垃圾邮件检查。私人邮箱能否长期满足业务量需实际确认，本批不购买新服务。

## 4. 迁移与候选切换

先在本机验证和打包，不在2GiB服务器执行Android构建。候选代码走独立评审分支，不混入现有Dockerfile修改。先备份恢复通过，再在网站短维护窗口执行已确认启动器对应的 Flask db upgrade，目标 `20261114_shared_identity`，并检查模型一致性。

迁移只追加 Member.auth_epoch(默认0)、email_verified_at(旧账号NULL)及四张identity表，不改旧密码/角色/ID/归属/资料。MySQL DDL可能自动提交且短暂锁表，不能把迁移描述成完全可事务回滚；如中断，按实际列/表现状修复后向前完成，不盲目重复执行或删除部分表。

反向代理限流：确认应用仍只监听127.0.0.1，Nginx覆写 `X-Forwarded-For $remote_addr` 和 `X-Forwarded-Proto $scheme`，而非信任用户原头。确认后可设 TRUST_LOOPBACK_PROXY=true，只信任本机来源的一层转发；默认关闭。用不同来源与伪造头验证限流，禁止根据语言或IP切换region。

部署候选、重启仅everhere服务，保持公网现状；先内部验证 health、首页、工作台、旧账号和原记录可用。SMTP、迁移、代理检查都通过后启用SHARED_IDENTITY_ENABLED=true，再验内部HTTPS的注册/登录/退出/找回。配置缺失不降级成测试邮箱或控制台验证码。

## 5. 手机与公网验收

仅当实际允许开放且HTTPS公网可达后，给cn包注入独立origin。先核对账号与同步入口的区分，防止将未部署的第二批同步作为可用能力。国际API保持空。code38未改源码本批不重新打包；后续有实际配置或UI改动时按Android版本规则构建并验证。

用两只新合成账号做Web注册→手机登录、手机注册→Web登录；真实收信/验证码错误与过期/进程重启/30天刷新边界/退出/找回/旧凭证撤销/普通用户拒绝管理员入口。旧用户登录由本人输入凭证，核对原ID与记录；手机游客资料不因登录上传。服务器内部curl通过、电脑公网浏览器通过、手机真机通过分别记录，不相互代替。

## 6. 停用与恢复

优先关闭SHARED_IDENTITY_ENABLED并保留新代码与追加表：网页隐藏新入口，手机接口503，原Web登录仍运行且继续检查auth_epoch。这是兼容停用方案，不丢已新建账号或改密结果。

不要直接把运行代码退回忽略auth_epoch的旧版本，否则旧Cookie可能恢复权限。若确须恢复旧代码，先撤销所有Cookie（安全更换SECRET_KEY），停用所有手机令牌，确认新密码和新账号仍被保留，单独审阅兼容方案。迁移downgrade明确拒绝自动删除身份表。

数据库恢复只能在停写、核对恢复点、保留故障现场和确认恢复期间增量数据处理后执行；旧快照可能丢新注册、改密、订单和相册更新，不能常规用回档代替代码修复。恢复后重新验证密码与会话撤销状态，必要时使所有会话失效；不声称现有备份已完成这些步骤。

## 恢复库排序规则与部分DDL（演练修正）

建立恢复库时应核对原库的默认字符集与排序规则；表级/列级规则也可能不同，不能只凭utf8mb4相同就认为外键兼容。共用身份迁移已显式继承旧members.id的有效列规则。若演练迁移已部分失败，保留该测试库，另建唯一命名的_test恢复库重新演练；不要把生产库回档或删除列当成常规修复。
