"""从唯一的英文文案字典生成无需构建工具的浏览器模块。"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
catalog = json.loads((ROOT/'app/locales/en.json').read_text(encoding='utf-8'))
assert all(isinstance(k, str) and isinstance(v, str) and v.strip() for k, v in catalog.items())
text = '/* 由 tools/build-i18n.py 生成；请编辑 app/locales/en.json。 */\nexport default '+json.dumps(catalog, ensure_ascii=False, indent=2)+';\n'
(ROOT/'app/static/js/messages-en.js').write_text(text, encoding='utf-8')
print(f'Generated {len(catalog)} English messages')
