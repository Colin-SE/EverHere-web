# 中国区共用身份：本地验证记录

日期：2026-11-14。候选源码基于 Web 重构版 `3a513e32cb00acf641bd1224cdf0d32488b1cd15`；Android未修改，远端main仍为 `9c4335e27e7f8054248c422e435dcafd5b40a283`。所有资料为合成数据。

## 最终结果

| 环境 | 检查 | 结果 |
|---|---|---|
| SQLite 全套 | 原Web范围及新增身份/兼容/代理/重启 | 116通过，5项跳过（4项须MySQL并发、1项须独立MySQL迁移库），0失败 |
| 本机 MySQL8.0.39 独立实例 | 身份定向、会话竞争、重发竞争、旧数据追加迁移 | 18通过，0跳过，0失败；其中持久重启用SQLite文件、代理为WSGI检查，其余使用独立MySQL测试库 |
| Edge/Playwright | Web注册→手机协议登录，手机协议注册→Web登录，错码保留输入、找回撤销旧token、Web刷新保持 | 通过 |
| 390px中文/英文 | 注册与找回入口、无横向溢出、无未处理JS错误 | 通过，已查看最终截图 |
| JavaScript/补丁 | node语法、git diff --check | 通过 |
| 服务器/公网/手机 | 生产迁移与真实旧用户、真实邮件送达、内部HTTPS、公网浏览器、手机安装重启 | 本轮未执行，不算已上线 |

MySQL为本任务临时创建，绑定127.0.0.1:13316，数据位于聊天work/mysql-data，与现有MySQL服务/网站库无关。测试只允许名称以 `_test` 结尾的数据库。追加迁移测试从旧迁移头插入合成旧账号、原密码哈希、空间归属及记录，再升级并对比模型，无结构差异。它不等于恢复了真实生产备份。

并发检查：同旧refresh/同operation同时刷新返回同凭证；同码并发注册只成功一次；同邮箱并发重发只有最后一封有效；密码KDF期间重置后旧密码不能建立新会话。另验证换号不能撤销他人会话、过期access可在服务重启后用refresh恢复、旧无epoch Cookie在找回后失效。

## 可重现检查

使用既有Python环境安装requirements.lock.txt，不读取生产.env。SQLite：

```sh
TEST_DATABASE_URL=sqlite:// python -m pytest -q
```

MySQL仅使用独立实例/空迁移库，配置 TEST_DATABASE_URL 与 IDENTITY_MIGRATION_TEST_URL，均必须是 `_test` 库，再执行：

```sh
python -m pytest tests/test_shared_identity.py tests/test_shared_identity_concurrency.py -q
```

浏览器：启动 `tools/shared-identity-check-server.py`（专用5017端口、内存SQLite、测试收件箱，不向外发邮件），运行 `node tools/shared-identity-browser-check.cjs`。截图在被忽略的test-results/shared-identity/。不要把此测试启动器用于真实资料或生产部署。

## 过程中发现和修正

- 首轮初始化同时读取session和capabilities时，两次新访客Cookie竞争，导致验证码请求CSRF403；改为先完成session再读capabilities，最终完整浏览器路径通过。
- 初始测试工具的本地网络进程不可互通，调整本任务测试进程的执行方式后继续验收，未把连接失败记成业务通过。
- 旧账号记录测试最初把数据库行ID误用为对外source_id；修正合成样本，单项与最终全套重新通过。实际代码继续保留这两种原有ID语义。
- 浏览器语言切换会重新载入登录页，测试改为进入英文注册后再检查；窄屏按钮换行已调整并查看截图。
- SQLite出现Python3.12日期适配弃用提示，没有失败；不影响本批身份结果，未为此改动既有资料层。

## 尚未完成

未取得可用服务器连接，没有重新证明生产运行SHA；交接中的内部HTTPS和备份证据仍属历史。网易私人邮箱的具体域名、SMTP开通及授权码尚未配置。公网仍按原限制，不因本次本地代码而开放。

Android现有AuthApi/IdentityManager/SessionVault协议已逐项对照，但没有新APK或真机证据，也未填入服务地址。配置手机前需处理账号与未接通的同步/注销入口边界；当前服务器对注销明确503，不能让用户误认为删除成功。第一批全部验收尚未完成。

资料同步、Fastify/PG与Web资料映射、照片、离线冲突、恢复，以及定时异地备份与真实备份恢复仍分别待做。本批未更改课程库、商城、支付、地球或人生脉络。

密码验证沿用 [Werkzeug官方API](https://werkzeug.palletsprojects.com/en/stable/utils/#werkzeug.security.check_password_hash)；轮换回执使用 [cryptography Fernet](https://cryptography.io/en/latest/fernet/)，不自行设计加密算法。

## 服务器恢复库演练补充（2026-11-14）

用户已完成生产备份下载及独立恢复；截图确认1个账号、0条记录/照片，密码/邮箱/角色与空间归属差异均为0。服务器真实运行3a513e3，迁移头20261102_product_images，Waitress本机5000、admin账户。候选dc72147通过离线bundle校验导入，运行版本未切换。

在恢复测试库试迁移时发现外键3780：原members.id为utf8mb4_unicode_ci，恢复库默认utf8mb4_0900_ai_ci，新会话表默认规则不兼容。正式库未执行本次迁移。测试失败已保留，不能在部分DDL已提交的测试库盲目重跑。

修复：只让新member_id外键沿用旧members.id的有效字符集/排序规则。MySQL反射可能省略旧表继承的规则，因此从information_schema读取列的实际值；不重写旧ID、密码或旧表。新增回归在旧表创建后改变独立测试库默认排序规则，再升级并核对旧数据与模型。SQLite/MySQL两项迁移回归最终通过；初版仅复制反射类型仍失败的记录保留。修复后的服务器复验另行记录，不冒充已部署。
