# 本轮实际验收记录

日期：2026-10-20。范围：Web核心功能对齐、旧功能与历史资料清理、按产品总规划v3出具完成度。Android工作区只读。

## 已通过

1. `.venv/Scripts/python.exe -m pytest -q`：65项全部通过。使用隔离内存SQLite，原生夹具为Android导出器生成的合成JSON/ZIP。含空库迁移与模型对齐检查；不连接真实人生资料库做破坏性测试。
2. 本机MySQL `127.0.0.1/lifealbumweb`：按授权清空历史账户/记录/关系/照片，不创建备份；升级到 `20261020_remove_legacy`；`flask --app wsgi db check` 输出无新升级操作。users表和is_private列已不存在。
3. `tools/run-check-server.py` 启动独立内存SQLite合成库，Edge执行 `tools/browser-check.cjs`。流程包括草稿刷新恢复、月精度1960-02、原图上传和大图、时间轴关闭仍在ALL可见、回收站原ID恢复、人物草稿正式提交及关联预填、原生ZIP预览确认恢复/JSON及原图ZIP下载、月精度不绘制假日历标记、FOREST刷新保留、390px无横向溢出。无页面未处理JS异常。
4. Node检查当前前端模块语法；Python加载业务模块及迁移。内存验收服务使用单线程，避免SQLite共享连接并发事务交错（正式MySQL使用连接池）。浏览器验收曾发现删除旧关系入口后数组未初始化，已改为人物关联展示并重新通过流程。

## 截图

截图仅包含本轮合成资料：

- [桌面外观页面](../test-results/current-desktop.png)
- [390px首页](../test-results/current-mobile.png)

`test-results`被Git忽略；旧截图已删除。截图不是Android实机、公网服务或用户最终设计验收。结束验收服务释放合成数据库，不留历史版本备份。

## 未验证与当前边界

### 需求与中英文适配补验（2026-10-23）

依据用户确认的 v3 原文和既定技术架构，验收表列出24模块、71项产品基线及10项问题，另补4项语言验收。需求原文摘要记录于 requirements.md，表格提供结果、能力缺口、代码/测试证据和后续验收，未把Android描述当作Web完成证据。

本轮 `.venv\Scripts\python.exe -m pytest -q` 全部87项通过；`node tools/lifegraph-state-check.mjs` 通过；Edge 的 `tools/browser-check.cjs`、`tools/lifegraph-browser-check.cjs`、`tools/i18n-browser-check.cjs` 全部通过。浏览器采用5003端口独立内存合成库，无真实日记或真实MySQL写入。

中英文检查覆盖主要视图、模板、系统错误、年月精度、界面语言持久化、编辑保护、跨语言草稿恢复、心情稳定枚举、原文姓名与归档保真、登录页、390px无横向溢出和语言入口。修复详情心情遗漏翻译、移动首页隐藏语言入口；草稿保存检查等待完整刷新结束再切换，避免把保存中保护误判为失效。

截图位于被Git忽略的 `test-results/i18n-home-en.png`、`i18n-mobile-en.png`、`i18n-graph-en.png`，仅含合成资料。旧的MySQL检查记录不代表本轮执行；最终用户视觉签收和全设备可访问性仍需另验。

未进行手机安装/反向恢复、真实公网共同服务、真实邮件/支付、生产部署/备份恢复、大档案性能及最终视觉验收。当前Web没有云资料执行功能，不把登录、健康检查或原生归档交换算作双端联网。

实际功能、未实现项及问题见 [完成度文档](feature-completion.md)。未来检查应根据新变更选择相关用例，不无理由重复全量构建。

## 人生脉络专项（2026-10-21）

本地完整后端81项通过；Node `tools/lifegraph-state-check.mjs`通过共享节点/循环/收起/删除复核。Edge `tools/lifegraph-browser-check.cjs`通过有限现在、查找聚焦、单层分页、原ID编辑返回、显式关联增删、画布平移、390px布局、断网重试与清Cookie隔离；使用5003端口内存合成库，不写真实MySQL资料。

代表画面为本轮合成资料：[桌面](../test-results/lifegraph-desktop.png)、[窄屏](../test-results/lifegraph-mobile.png)。截图被Git忽略，仅作本地可审阅产物；不是物理手机或最终用户设计验收。本地阶段未重新执行MySQL业务全套；v1.1提交后由GitHub Actions专用_test库检查，最终以PR当前提交结果为准。生产/Android/云端验收仍未执行。

发现并修复：Windows缺IANA时区包、合成归档关联ID需按原生规则排序、清Cookie后旧CSRF无法复核；补充tzdata依赖、生成器排序、先恢复会话后验证当前空间。读取失败继续显示错误与重试，不伪装空成功。

真实MySQL `flask --app wsgi db check`再次通过，无新增结构差异；本轮不写真实业务资料。人生脉络后端81项检查、独立Node状态检查及原有浏览器主流程均通过；另补验证日期筛选、原详情编辑前后相同视口、后台关闭阅读弹窗与空间切换断网重试。
