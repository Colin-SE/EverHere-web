"""对齐 Android RecordQuery：日期窗口只用于比较，不改原日期。"""
import re
from flask import g
from sqlalchemy import select

from ..extensions import db
from ..models import LifeRecord
from ..security import APIError
from sync_contract import event_date


def record_date(value):
    native = value.get('androidDocument', {})
    if isinstance(value.get('eventDate'), dict):
        raw = value['eventDate']
    else:
        start = value.get('eventStartAt', value.get('eventDate')) or None
        end = value.get('eventEndAt') or None
        precision = value.get('datePrecision', 'range' if end else 'day' if start else 'unknown')
        raw = {'precision': precision, 'start': start, 'end': end}
    return event_date(raw)


def window(value):
    precision, start, end = value['precision'], value['start'], value['end']
    if precision == 'unknown':
        return None
    def parts(text):
        match = re.fullmatch(r'([+-]?[0-9]+)(?:-([0-9]{2}))?(?:-([0-9]{2}))?', text)
        return int(match[1]), int(match[2] or 1), int(match[3] or 1)
    left = parts(start)
    if precision == 'year':
        return left, (left[0], 12, 31)
    if precision == 'month':
        y, m, _ = left
        leap = y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)
        last = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m-1]
        return left, (y, m, last)
    return left, parts(end) if precision == 'range' else left


def select_records(args):
    from .records import record_data, STATES
    target = args.get('target', 'all')
    if target not in ('all', 'timeline', 'spatial'):
        raise APIError('查询范围无效。')
    if 'vault' in args:
        raise APIError('旧保险箱功能已删除。', 404)
    trash = args.get('trash') == 'true'
    query = select(LifeRecord).where(LifeRecord.user_id == g.owner.id, LifeRecord.is_deleted.is_(trash))
    state, precision, progress = args.get('state'), args.get('precision'), args.get('progress')
    if state and state not in STATES:
        raise APIError('记录状态无效。')
    if precision and precision not in ('day', 'month', 'year', 'range', 'unknown'):
        raise APIError('日期精度筛选无效。')
    if progress and progress not in ('all', 'unfinished', 'planned', 'started', 'completed', 'cancelled'):
        raise APIError('进展筛选无效。')
    bounds = []
    for key in ('from', 'to'):
        raw = args.get(key)
        bounds.append(window(event_date({'precision': 'day', 'start': raw, 'end': None}))[0] if raw else None)
    lower, upper = bounds
    if lower and upper and lower > upper:
        raise APIError('筛选的截止日期不能早于起始日期。')
    words = args.get('q', '')[:200].casefold().split()
    people = args.get('people', '').split(',') if args.get('people') else []
    if len(people)>100:
        raise APIError('人物筛选过多。')
    if args.get('node'):
        from ..models import LifeNode
        node = db.session.scalar(select(LifeNode).where(LifeNode.user_id == g.owner.id, LifeNode.source_id == args['node'], LifeNode.kind == args.get('kind', 'entities'), LifeNode.is_deleted.is_(False)))
        if not node:
            raise APIError('关联对象不存在。', 404)
    selected = []
    for row in db.session.scalars(query):
        value = record_data(row)
        if target == 'timeline' and not value.get('showInTimeline', True):
            continue
        if target == 'spatial' and (not value.get('showOnGlobe', False) or value.get('latitude') is None or value.get('longitude') is None):
            continue
        if state and value['recordState'] != state or precision and value['datePrecision'] != precision:
            continue
        completion = value['completionState']
        if progress == 'unfinished' and completion not in ('planned', 'started') or progress and progress not in ('all', 'unfinished', completion):
            continue
        event = window(record_date(value))
        if lower and (event is None or event[1] < lower) or upper and (event is None or event[0] > upper):
            continue
        fields = [value['title'], value['content'], value.get('placeName') or '', value.get('mood') or '', *value.get('tags', [])]
        if not all(any(word in field.casefold() for field in fields) for word in words):
            continue
        if args.get('tag') and args['tag'] not in value.get('tags', []):
            continue
        if not set(people).issubset(value.get('linkedEntityIds', [])):
            continue
        if args.get('node') and args['node'] not in value.get({'entities':'linkedEntityIds','threads':'linkedThreadIds','chapters':'linkedChapterIds'}.get(args.get('kind','entities'), 'linkedEntityIds'), []):
            continue
        selected.append(value)
    selected.sort(key=lambda v: v['id'])
    selected.sort(key=lambda v: window(record_date(v))[0] if window(record_date(v)) else (-1000000000,1,1), reverse=True)
    return selected
