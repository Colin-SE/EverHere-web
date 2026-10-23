"""将验收数据呈现为可直接阅读和版本管理的 Markdown，不改变验收结果。"""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT / 'docs/acceptance-2026-10-22.json').read_text(encoding='utf-8'))
rows = data['rows']
counts = Counter(row['status'] for row in rows)


def cell(value):
    return str(value).replace('|', r'\|').replace('\n', '<br>')


lines = [
    '# Everhere Web 功能验收报告', '',
    '产品基线核对：2026-10-22；中英文补验及文档交付：2026-10-23。', '',
    '需求依据：[完整产品总规划 v3](product-plan-v3.md)。技术架构以 [当前需求基准](requirements.md) 为准，沿用 Web Flask/MySQL、Android SQLite 及独立共同云。', '',
    '本报告替代此前 Excel 交付，保留全部验收结果、证据、缺口和后续步骤。本次仅转换文档格式，没有重新执行功能验收。', '',
    '## 验收总览', '',
    '| 范围 | 验收点 | 通过 | 部分通过 | 未实现 | 待验证 |',
    '|---|---:|---:|---:|---:|---:|',
    '| 产品规划基线 | 71 | 30 | 8 | 30 | 3 |',
    '| 中英文适配补验 | 4 | 4 | 0 | 0 | 0 |',
    f"| 合计 | {len(rows)} | {counts['通过']} | {counts['部分通过']} | {counts['未实现']} | {counts['待验证']} |", '',
    '统计只代表已列验收点，不是整体产品完成百分比。“通过”仅限该项注明的能力与环境，不能外推整个模块或生产环境已完成。', '',
    '- **通过**：已有子功能具备代码和本轮检查证据。',
    '- **部分通过**：已有可运行子集，仍存在缺口。',
    '- **未实现**：没有可用的完整产品流程；协议或模型预留不算实现。',
    '- **待验证**：缺少所需环境、实机或人工签收证据。', '',
    '## 模块总览', '',
    '| 模块 | 验收点 | 通过 | 部分通过 | 待补项 | 剩余缺口 |',
    '|---|---:|---:|---:|---:|---|',
]
for module in data['modules']:
    subset = [row for row in rows if row['section'] == module['section']]
    states = Counter(row['status'] for row in subset)
    lines.append('| ' + ' | '.join(map(cell, [module['name'], len(subset), states['通过'], states['部分通过'], states['未实现'] + states['待验证'], module['gap']])) + ' |')
lines += ['', '“待补项”包含未实现与待验证。跨模块架构和语言验收计入顶部总数，详见以下独立章节。', '', '## 逐项验收', '']
names = {module['section']: module['name'] for module in data['modules']}
names.update({'8/9': '8/9 架构与多端规则', 'WEB-I18N-01': 'WEB-I18N-01 中英文适配'})
for section in dict.fromkeys(row['section'] for row in rows):
    lines += [f'### {names[section]}', '']
    for row in (row for row in rows if row['section'] == section):
        lines += [f"#### {row['id']} · {row['feature']}", '',
                  f"- **结果：{row['status']}**", f"- 实际能力与缺口：{row['result']}",
                  f"- 代码与检查证据：{row['evidence']}", f"- 后续验收：{row['next']}", '']
lines += ['## 已知问题与处理方向', '', '| 编号 | 问题 | 影响与当前行为 | 后续处理 |', '|---|---|---|---|']
for issue in data['issues']:
    lines.append('| ' + ' | '.join(map(cell, issue)) + ' |')
lines += ['', '## 证据与验收边界', '',
          '2026-10-23检查记录：后端87项通过，Node状态检查通过，Edge中文主流程、人生脉络及中英文专项通过。详见 [执行记录](verification.md) 和 [语言适配说明](i18n.md)。', '',
          '环境为独立 SQLite/Edge 合成库；不写真实业务资料。本轮未重新执行真实MySQL业务全套、Android实机反向恢复、真实共同云、支付/邮件、生产部署及用户最终视觉签收。', '',
          '需求原文 SHA-256：`' + data['sourceSha256'] + '`。', '',
          '逐项数据源：[acceptance-2026-10-22.json](acceptance-2026-10-22.json)。修改数据后运行 `python tools/render-acceptance.py` 更新本文。', '']
target = ROOT / 'docs/acceptance-2026-10-22.md'
target.write_text('\n'.join(lines), encoding='utf-8')
assert sum(line.startswith('#### WEB-') for line in lines) == len(rows) == 75
assert len(data['modules']) == 24 and len(data['issues']) == 10
print(f'Generated {target.name}: 75 items, 24 modules, 10 issues')
