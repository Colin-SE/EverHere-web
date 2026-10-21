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

未进行手机安装/反向恢复、真实公网共同服务、真实邮件/支付、生产部署/备份恢复、大档案性能及最终视觉验收。当前Web没有云资料执行功能，不把登录、健康检查或原生归档交换算作双端联网。

实际功能、未实现项及问题见 [完成度文档](feature-completion.md)。未来检查应根据新变更选择相关用例，不无理由重复全量构建。
