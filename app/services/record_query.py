"""对齐 Android RecordQuery：日期窗口只用于比较，不改原日期。"""
import re
from flask import g
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..extensions import db
from ..models import LifeRecord
from ..security import APIError
from .record_schema import event_date


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


def select_records(args, page=None, size=30):
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
    if state:
        query = query.where(LifeRecord.record_state == state)
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
    needs_links = bool(people or args.get('node'))
    if page is not None and not needs_links:
        # 先读筛选与排序所需字段，后按稳定的日期/ID 顺序加载当页正文和关系。
        base = [LifeRecord.id, LifeRecord.source_id, LifeRecord.payload]
        if words:
            base += [LifeRecord.title, LifeRecord.content]
        candidates = db.session.execute(query.with_only_columns(*base)).yield_per(100)
    else:
        candidates = db.session.scalars(query.options(selectinload(LifeRecord.links))).yield_per(100)
    for row in candidates:
        value = (dict(row.payload) if page is not None and not needs_links else record_data(row))
        if target == 'timeline' and not value.get('showInTimeline', True):
            continue
        if target == 'spatial' and not ((value.get('placeName') or '').strip() or
                (value.get('showOnGlobe', False) and value.get('latitude') is not None and value.get('longitude') is not None)):
            continue
        if precision and value['datePrecision'] != precision:
            continue
        completion = value['completionState']
        if progress == 'unfinished' and completion not in ('planned', 'started') or progress and progress not in ('all', 'unfinished', completion):
            continue
        event = window(record_date(value))
        if lower and (event is None or event[1] < lower) or upper and (event is None or event[0] > upper):
            continue
        if words:
            fields = [row.title, row.content, value.get('placeName') or '', value.get('mood') or '', *value.get('tags', [])]
            if not all(any(word in field.casefold() for field in fields) for word in words):
                continue
        if args.get('tag') and args['tag'] not in value.get('tags', []):
            continue
        if not set(people).issubset(value.get('linkedEntityIds', [])):
            continue
        if args.get('node') and args['node'] not in value.get({'entities':'linkedEntityIds','threads':'linkedThreadIds','chapters':'linkedChapterIds'}.get(args.get('kind','entities'), 'linkedEntityIds'), []):
            continue
        selected.append((event[0] if event else (-1000000000, 1, 1), row.source_id,
                         row.id if page is not None else value))
    selected.sort(key=lambda item: item[1])
    selected.sort(key=lambda item: item[0], reverse=True)
    if page is None:
        return [item[2] for item in selected]
    start = (page - 1) * size
    ids = [item[2] for item in selected[start:start + size]]
    rows = {row.id: row for row in db.session.scalars(select(LifeRecord).where(
        LifeRecord.user_id == g.owner.id, LifeRecord.id.in_(ids), LifeRecord.is_deleted.is_(trash),
    ).options(selectinload(LifeRecord.links)))}
    return [record_data(rows[id]) for id in ids if id in rows], len(selected)
