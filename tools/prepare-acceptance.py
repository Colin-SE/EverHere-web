"""整理需求验收清单；仅依据已读代码与实际检查，不生成模拟完成率。"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
rows = []


def add(section, feature, status, result, evidence, next_step="无需补充本行已定义的本机行为；生产与实机另验"):
    rows.append({"id": f"WEB-{section}-{sum(r['section'] == section for r in rows)+1:02}", "section": section,
                 "feature": feature, "status": status, "result": result, "evidence": evidence, "next": next_step})


add('4.1', '首页近期、最近编辑、进行中、计划与真实入口', '通过', '读取同一份正式记录，草稿与回收站独立；统计可进入筛选结果', 'app/static/js/views.js: home；tools/browser-check.cjs')
add('4.1', '最终手机视觉与全页面一致性', '待验证', '桌面与390px合成浏览器路径已有证据；不等于物理手机或用户视觉签收', 'tools/browser-check.cjs；docs/verification.md', '补实际设备、大字和用户视觉验收')
add('4.2', '三种创作状态、同ID编辑与人物预填', '通过', '已发生、进行中、计划共用编辑器；修改保持ID', 'tests/test_application.py；tools/browser-check.cjs')
add('4.2', '草稿自动保存、恢复、放弃与冲突保护', '通过', '600ms自动保存，记录与人物草稿独立；重复提交幂等、冲突保留输入', 'test_draft_raw_values_restart_conflict_and_commit_receipt；浏览器草稿刷新路径')
add('4.2', '那一天、影音、萌宠创作入口', '未实现', '目前没有完整六入口；不开放假入口', 'app/templates/index.html: creation-dialog；app/static/js/app.js', '先完成提醒、影音和宠物业务，再接统一编辑器')
add('4.2', '浏览器离线写入与突然退出保护', '部分通过', '已被服务端确认的草稿可恢复；断网或最后600ms输入不保证持久化', 'app/static/js/drafts.js；app/static/js/app.js: beforeunload', '设计授权离线缓存、生命周期和多标签冲突')
add('4.3', '日、月、年、范围、未知及事件时区', '通过', '保留日期精度与事件时间，不用创建时间替代；扩展年份原文保真', 'test_dates_preserve_exact_precision_and_raw_text；test_actual_android_json_roundtrip_and_edit_preserve_raw_fields')
add('4.3', '计划转实际、取消和独立完成状态', '通过', '确认真实日期后更新原ID，日期过去不自动完成', 'test_plan_to_fact_requires_actual_date_but_progress_is_independent')
add('4.3', '照片EXIF日期辅助与空日期候选', '未实现', '未对齐规划引用code24/25的日期帮助', 'app/static/js/app.js: configureDates/openEditor', '读取有效拍摄日作候选，用户已有输入优先；取消不提交')
add('4.3', '扩展年份新建与跨期日历完整交互', '部分通过', '归档可保真；交互年份范围与HTML日期控件仍有限制', 'app/static/js/app.js: configureDates；app/static/js/record-date.js', '补负年份、大年份和超长范围的人机交互')
add('4.4', '多图上传、原字节、顺序与批量失败原子性', '通过', '最多10张，单图50MiB/100MP；原字节保留，失败批次不部分提交', 'test_photo_original_bytes_and_failed_batch_are_atomic；tools/browser-check.cjs')
add('4.4', '全屏原图、缩放、切换与失败重试', '通过', '详情和编辑照片可打开独立查看器；失败保留引用', 'app/static/js/gallery.js；tools/browser-check.cjs')
add('4.4', '拖动排序、缩略图流水线与孤立资源回收', '未实现', '现有顺序保留，但无完整排序与资源回收流程', 'app/api/records.py；app/static/js/app.js', '补引用计数、缩略图、延迟回收和显式清理')
add('4.4', '安卓同等级私有加密照片和云原图进度', '未实现', 'Web普通原图未提供安卓同等级加密或云传输闭环', 'app/models.py；app/api/records.py；app/api/cloud.py', '按Web密钥和共同云协议独立实现')
add('4.5', '统一详情、原ID编辑、软删除与恢复', '通过', '多个视图指向同一记录；恢复保留原ID、关系和照片', 'test_soft_delete_restores_original_id_relations_and_photos；tools/browser-check.cjs')
add('4.5', '永久删除及照片资源回收', '未实现', '仅开放软删除和恢复', 'app/api/records.py；app/static/js/views.js: trash', '定义范围、确认、引用规则和失败恢复')
add('4.5', '各入口返回后的完整滚动位置', '部分通过', '查询路由状态和脉络视口有保留；普通列表滚动位置未完整保留', 'app/static/js/app.js: writeRoute/restoreRoute；tools/lifegraph-browser-check.cjs', '补普通列表详情返回滚动恢复')
add('4.6', '时间轴按事件日期与状态展示', '通过', '显示开关只影响时间轴，ALL保持独立查询', 'test_query_targets_words_progress_and_date_overlap；tools/browser-check.cjs')
add('4.6', '日历翻月、跳月、选日新增与粗精度单列', '通过', '月/年/未知不画虚假精确日标记；选日可预填', 'app/static/js/record-date.js；tools/browser-check.cjs')
add('4.7', '关键词、状态、进展、日期、标签、多人物筛选', '通过', '多关键词全匹配、日期重叠、多人物同时关联；统计读真实资料', 'test_query_targets_words_progress_and_date_overlap；app/services/record_query.py')
add('4.7', '完整对象筛选、高级回顾与大档案分页', '部分通过', '人物和已支持条件可用；其他对象业务及服务端分页未完整实现', 'app/services/record_query.py；app/static/js/views.js', '扩展对象上线后补筛选；建立大档案性能样本')
add('4.8', '人物创建、编辑、同名独立、搜索和相关经历', '通过', '人物独立草稿；从人物新建经历预填关系', 'test_people_drafts_same_names_and_unlink_preserve_record；tools/browser-check.cjs')
add('4.8', '删除人物只解绑、保留经历与原图', '通过', '删除人物不级联删除原事件', 'test_people_drafts_same_names_and_unlink_preserve_record')
add('4.8', '人物封面、完整资料与人物间关系', '未实现', '目前提供名称和意义；没有完整人物间语义关系编辑', 'app/api/graph.py；app/static/js/app.js: openNode', '定义资料与关系语义、迁移及归档兼容')
add('4.9', '宠物分类档案、生日/到家日及成长经历', '未实现', '原生协议保留类型，脉络可展示导入对象；没有创建和管理闭环', 'sync_contract.py；app/api/graph.py', '实现宠物独立资料与统一记录关联')
add('4.9', '物品档案、来源、意义及跨阶段经历', '未实现', '协议保留不等于物品产品页面', 'sync_contract.py；app/api/graph.py', '实现物品资料和删除解绑规则')
add('4.10', '文字地点、合法坐标、精度与空间查询', '通过', '无坐标可保存文字；0坐标有效；仅显示开启空间展示的合法记录', 'app/services/records.py；app/services/record_query.py；tests/test_application.py')
add('4.10', '独立地点、工作和自定义对象档案', '未实现', '旧泛对象页已移除，work含义保留', 'app/api/graph.py；sync_contract.py', '按规划定义完整对象页')
add('4.10', '高德地址搜索、选点与主动定位', '未实现', '仅完成选型调研，未配置或接入地图服务', 'app/config.py；app/static/js/views.js: places', '确认坐标系、服务密钥、授权和双端兼容后实现')
add('4.11', '影音作品库、分类、评分与多次体验', '未实现', '没有可用影音业务页面', 'app/api/graph.py；app/static/js/views.js', '区分作品资料与个人事件日期、进展')
add('4.12', '阶段命名、日期精度、重叠阶段与未来阶段', '未实现', '仅保留LifeChapter原生协议与图谱投影', 'sync_contract.py；app/services/lifegraph.py', '实现阶段列表、详情和独立编辑流程')
add('4.12', '阶段规划、回顾与候选关联确认', '未实现', '没有完整规划/回顾字段与页面闭环', 'app/models.py；app/api/graph.py', '追加兼容模型，完成CHAPTER-PLAN-01专项')
add('4.13', '长期投入列表、详情、状态与容器内新增', '未实现', 'LifeThread仅保留协议语义；脉络可读既有关联', 'sync_contract.py；app/services/lifegraph.py', '定义完整容器业务与预填关系')
add('4.14', 'NOW：现在有限邻域与事件时间解释', '通过', '过去30天至未来14天及进行中，每页6项；不按最近编辑推断重要性', 'test_now_is_limited_time_context_not_recently_edited；tools/lifegraph-browser-check.cjs')
add('4.14', 'EXPAND：一层展开、分页、收起、聚焦与去重', '通过', '共享节点与环去重；视图最多80节点；可回到现在和筛选', 'tests/test_lifegraph.py；tools/lifegraph-state-check.mjs；tools/lifegraph-browser-check.cjs')
add('4.14', 'LINK：同ID详情跳转与视口返回', '通过', '从图谱进入原详情编辑后保留当前探索上下文', 'tools/lifegraph-browser-check.cjs；app/static/js/lifegraph.js')
add('4.14', 'REL：既有正式关联增删和来源说明', '通过', '显式确认、版本校验；解除不删正文原图；不推断共同参与者亲密关系', 'test_explicit_link_unlink_updates_same_fact_and_native_archive_preserves_draft；tests/test_lifegraph.py')
add('4.14', 'PRIV/COMPAT：当前空间隔离与归档保真', '通过', '删除与跨空间不能继续显示；正式关联通过原生归档保存', 'test_spaces_and_deleted_or_protected_data_never_enter_graph；test_native_record_relation_edit_preserves_original_fields_photos_and_audit')
add('4.14', '新语义关系、完整对象详情、布局跨端', '未实现', '仅既有关联；没有人物间因果/影响语义及布局同步', 'app/services/lifegraph.py；docs/lifegraph.md', '先定义新关系方向、来源、时间与迁移')
add('4.14', '物理手机手势、海量性能与最终设计签收', '待验证', '现有证据限Edge合成库及390px视口', 'tools/lifegraph-browser-check.cjs；docs/verification.md', '真机、大档案和用户代表画面验收')
add('4.15', '未来计划、待安排、改期、取消和确认发生', '通过', '未来入口读取同源计划，过期不自动变成已发生', 'app/static/js/views.js: upcoming；test_plan_to_fact_requires_actual_date_but_progress_is_independent')
add('4.15', '往年今天、纪念日与解释性统计回顾', '未实现', '没有完整那一天或高级回顾页面', 'app/static/js/views.js', '按真实事件日期生成回顾并可回到原详情')
add('4.15', '提醒权限、调度、闰日时区及取消旧任务', '未实现', '导入仅保存提醒元信息，不启动系统通知', 'sync_contract.py；tests/test_local_android.py', '定义各端调度与去重、拒绝权限后行为')
add('4.16', '同源地点列表与显示开关', '通过', '已有地点列表，点击原记录；缺坐标不猜点位', 'app/static/js/views.js: places；app/services/record_query.py')
add('4.16', '真实3D地球、国家区域聚合和点位抽屉', '未实现', '尚无3D渲染器；静态图或列表不算地球', 'app/static/js/views.js: places', '按Globe.gl/MapLibre选型实现真实空间闭环')
add('4.16', '地球姿态、主题、遮挡、离线资源和手机手势', '未实现', '依赖真实地球功能', 'docs/product-plan-v3.md: 4.16', '地球实现后专项验收')
add('4.17', '游客本机空间与登录不上传资料', '通过', '无账号可用；云登录只验证身份，不上传正文照片', 'test_default_local_space_headers_and_removed_features；test_cloud_login_only_calls_auth_and_does_not_upload')
add('4.17', '共同云真实登录、注册邮件、找回与会话续期', '部分通过', '登录BFF和受控请求测试存在；无真实公网账号闭环、刷新和真实邮件', 'app/api/cloud.py；tests/test_local_android.py', '在可达同区共同云上完成真实账号路径')
add('4.17', '游客合并、换号清理、注销与空间找回', '未实现', '清Cookie会进入新空间，原数据无界面找回入口', 'app/security.py: load_user；app/api/cloud.py', '设计安全归属和恢复，不恢复旧本地密码账号')
add('4.18', '权益和范围许可不足时阻止同步', '通过', '本机标志不能授予权益；缺共同服务能力时保持关闭', 'test_client_flag_cannot_grant_entitlement_or_scoped_sync')
add('4.18', '授权开启、方向范围预览、队列上传下载', '未实现', '共同服务尚缺有效权益和单次范围许可，资料同步未接通', 'app/api/cloud.py；docs/cloud-sync.md', '服务端先提供授权契约，再完成队列、确认和重试')
add('4.18', '四种云冲突、删除传播和换机原图恢复', '未实现', '归档冲突复制不能代替联网同步', 'app/api/cloud.py；app/services/archive.py', '验证双端编辑、离线删除、照片独立恢复')
add('4.19', '基础空间隔离、CSRF、不缓存和受保护导入拒绝', '通过', '普通资料授权约束；受保护格式不降级为明文导入', 'tests/test_application.py；tests/test_local_android.py；app/__init__.py')
add('4.19', 'Web正文/原图加密、独立解锁和后台保护', '未实现', '未提供安卓同等级加密；旧保险箱实现已删除', 'app/models.py；app/api/records.py；docs/requirements.md', '重新设计Web密钥、解锁、索引过滤及缓存保护')
add('4.19', '保险箱完整闭环及可选跨端密钥恢复', '未实现', '规划目标保留，但没有可用保险箱入口', 'docs/product-plan-v3.md: 4.19；app/templates/index.html', '按完整锁定泄漏与恢复边界独立实现')
add('4.20', '原生普通JSON/ZIP预览、确认与原字节恢复', '通过', 'JSON无原图，完整ZIP需校验；恢复保留原ID、日期、关系和原图', 'test_actual_android_json_roundtrip_and_edit_preserve_raw_fields；test_actual_android_zip_restores_original_bytes_and_exports_valid_zip；tools/browser-check.cjs')
add('4.20', '重复、冲突复制、缺图确认与目标变化复核', '通过', '重复跳过，同ID冲突需明确选择；目标变化不覆盖', 'test_import_conflicts_copy_deterministically_without_overwrite；test_import_preview_rechecks_target_and_occupying_draft')
add('4.20', '坏归档/路径穿越拒绝和暂存加密清理', '通过', '校验失败原子拒绝；暂存加密，显式放弃可清理', 'test_zip_traversal_duplicate_and_changed_original_reject；test_stage_is_encrypted_and_explicit_discard_removes_it')
add('4.20', '大归档、旧复杂格式和Android反向实机恢复', '部分通过', 'JSON16MiB、ZIP128MiB；旧Web/受保护格式拒绝；无安卓反向实机证据', 'app/services/archive_files.py；sync_contract.py；docs/verification.md', '按支持范围统一上限，并完成真实双端恢复验收')
add('4.21', '选定范围Markdown/HTML事件簿', '未实现', '目前仅全空间普通数据归档', 'app/api/archive.py；app/static/js/views.js: archive', '实现选择、排版预览、敏感字段与原图范围')
add('4.21', 'PDF/图片输出与系统分享', '未实现', '没有排版输出闭环；公开链接非自动承诺范围', 'app/api/archive.py', '明确格式和授权后单独实现')
add('4.22', '我的、数据管理、回收站、草稿与两主题', '通过', 'WARM/FOREST保存浏览器偏好；切换不改事实资料', 'app/static/js/views.js；tools/browser-check.cjs')
add('4.22', '主题下载、付费主题与恢复默认专页', '未实现', '仅两套内置主题', 'app/static/js/views.js: appearance', '有真实主题资源和权益后实现')
add('4.22', '完整帮助、协议、反馈、偏好与可访问性', '部分通过', '已有关于与基础标签；缺完整渠道及大字/读屏验收', 'app/templates/index.html；app/static/js/views.js: about', '补可用支持渠道、全页键盘/读屏和大字检查')
add('4.23', '商品、支付、订单核验与幂等权益发放', '未实现', '没有购买入口和真实商品；不靠主题或客户端标志授予权益', 'app/api/cloud.py；docs/cloud-sync.md', '明确商品与渠道后实现服务端核验')
add('4.23', '恢复购买、到期退款、容量与支持', '未实现', '没有商业闭环', 'docs/product-plan-v3.md: 4.23；app/api/cloud.py', '处理全状态并保障已有资料查看和导出')
add('4.24', 'Flask API、迁移、配置向导与健康检查', '通过', '核心API及空库迁移经隔离检查；真实启动指向MySQL', 'test_empty_database_migration_matches_current_models；tests/test_mysql_setup.py')
add('4.24', '当前真实MySQL业务全套与生产环境', '待验证', '本轮基线运行SQLite；之前MySQL/CI证据不冒充本轮现场执行', 'docs/verification.md；tests/conftest.py', '专用_test数据库和目标部署环境分别验收')
add('4.24', '公网HTTPS、真实邮件、监控审计和恢复演练', '未实现', '尚无完整生产与运营交付', 'docs/cloud-sync.md；README.md', '集中明确服务配置与运营职责后实施')
add('8/9', '沿用用户指定Web/Android/共同云架构', '通过', 'Web Flask/MySQL；Android SQLite/SQLCipher不改；共同云独立PostgreSQL', 'docs/requirements.md；app/config.py；sync_contract.py')
add('8/9', '区域隔离与跨端协议兼容', '部分通过', '普通归档地区与字段严格校验；真实多端云与新旧客户端尚未联调', 'tests/test_local_android.py；sync_contract.py', '补同区真实双端、版本混用与新关系兼容')

# 模块总表取现有完成度文档，保留每个模块缺口。
add('WEB-I18N-01', '中英文选择、刷新持久化与移动入口', '通过', '2026-10-23补验：主页面和登录页可切换，390px入口可见', 'tools/i18n-browser-check.cjs；tests/test_i18n.py')
add('WEB-I18N-01', '现有视图、表单、系统文案、日期和错误提示', '通过', '2026-10-23补验：主要视图英文无遗漏中文系统文案；月精度双向显示', 'tools/i18n-browser-check.cjs；app/locales/en.json')
add('WEB-I18N-01', '用户原文、地区、协议值与归档保真', '通过', '2026-10-23补验：中文正文姓名保留，心情稳定枚举和归档事实不改变', 'tests/test_i18n.py；tools/i18n-browser-check.cjs')
add('WEB-I18N-01', '编辑切换保护和草稿跨语言恢复', '通过', '2026-10-23补验：编辑中阻止重载；保存草稿后换语言可恢复并提交', 'tools/i18n-browser-check.cjs；docs/i18n.md')

modules = []
for line in (ROOT/'docs/feature-completion.md').read_text(encoding='utf-8').splitlines():
    if re.match(r'\| 4\.\d+ ', line):
        cells = [v.strip() for v in line.strip('|').split('|')]
        modules.append({'section': cells[0].split()[0], 'name': cells[0], 'implementation': cells[1], 'available': cells[2], 'gap': cells[3]})
assert len(modules) == 24
issues = []
for line in (ROOT/'docs/feature-completion.md').read_text(encoding='utf-8').splitlines():
    if re.match(r'\| P\d+ ', line):
        issues.append([v.strip() for v in line.strip('|').split('|')])

data = {'date': '2026-10-22', 'scope': '当前Web工作区，独立SQLite与Edge合成资料；Android与真实共同云未执行',
        'source': 'docs/product-plan-v3.md（用户本次确认的完整产品需求）；技术架构以docs/requirements.md为准',
        'sourceSha256': 'a9c17a4ed1dc855783887387f40ba7f44dafb09365e59daf40d6be74a9da160f',
        'rows': rows, 'modules': modules, 'issues': issues}
(ROOT/'docs/acceptance-2026-10-22.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(f'Prepared {len(rows)} acceptance items, {len(modules)} modules and {len(issues)} issues')
