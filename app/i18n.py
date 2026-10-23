"""界面语言独立于地区、资料归属和同步；只翻译明确的显示文案。"""
import json
import re
from functools import lru_cache
from pathlib import Path

from flask import has_request_context, request


@lru_cache(maxsize=1)
def english_catalog():
    return json.loads((Path(__file__).parent/'locales/en.json').read_text(encoding='utf-8'))


def ui_locale():
    if not has_request_context():
        return 'zh-CN'
    value = request.headers.get('X-Everhere-Language') or request.cookies.get('everhere-language')
    return 'en' if value == 'en' else 'zh-CN'


def translate(source, **values):
    message = english_catalog().get(source, source) if ui_locale() == 'en' else source
    return re.sub(r'\{([a-zA-Z0-9_]+)\}', lambda match: str(values.get(match[1], match[0])), message)


def error_message(source):
    """参数化校验错误只翻译字段名称，不修改请求数据。"""
    if ui_locale() != 'en' or source in english_catalog():
        return translate(source)
    patterns = [
        (r'^(.+?) 须为布尔值。$', '{0} 须为布尔值。'),
        (r'^(.+?)须为不超过 (\d+) 字的文字。$', '{0}须为不超过 {2} 字的文字。'),
        (r'^(.+?)须为最多 (\d+) 项的列表。$', '{0}须为最多 {2} 项的列表。'),
        (r'^(.+?)须为有效日期。$', '{0}须为有效日期。'),
        (r'^(.+?)格式无效。$', '{0}格式无效。'),
        (r'^(.+?)无效。$', '{0}无效。'),
    ]
    for pattern, key in patterns:
        match = re.fullmatch(pattern, source)
        if match:
            return translate(key, **{'0': translate(match[1]), '2': match[2] if len(match.groups()) > 1 else ''})
    return translate(source)
