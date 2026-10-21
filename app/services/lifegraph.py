"""人生脉络是正式事实的授权投影，不保存画布副本或推测关系。"""
from datetime import datetime, timedelta
from heapq import nsmallest

from flask import current_app, g
from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy import select

from ..extensions import db
from ..models import LifeNode, LifeRecord, RecordNode, now
from ..security import APIError
from .record_query import record_date, window
from .records import identifier, record_data
from sync_contract import event_date

KINDS = {'entity': 'entities', 'chapter': 'chapters', 'thread': 'threads'}
TYPES = {'record', 'chapter', 'thread', 'person', 'pet', 'object', 'place', 'work', 'media', 'custom'}
LABELS = {'record': '人生记录', 'person': '人物', 'pet': '宠物', 'object': '物品', 'place': '地点', 'work': '工作', 'media': '影音', 'custom': '对象', 'chapter': '人生阶段', 'thread': '长期投入', 'now': '时间锚点'}
PAGE = 6


def graph_today():
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    if not hasattr(g, 'lifegraph_today'):
        try:
            g.lifegraph_today = datetime.now(ZoneInfo(current_app.config.get('EVENT_TIMEZONE', 'Asia/Shanghai'))).date()
        except (ZoneInfoNotFoundError, ValueError):
            raise APIError('事件时区配置不可读取，请安装tzdata并检查EVENT_TIMEZONE。', 503, 'graph_timezone_unavailable') from None
    return g.lifegraph_today


def key(row):
    kind = 'record' if isinstance(row, LifeRecord) else {'entities': 'entity', 'chapters': 'chapter', 'threads': 'thread'}[row.kind]
    return kind + ':' + row.source_id


def record_query():
    return select(LifeRecord).where(LifeRecord.user_id == g.owner.id, LifeRecord.is_deleted.is_(False), LifeRecord.privacy == 'standard')


def node_query():
    return select(LifeNode).where(LifeNode.user_id == g.owner.id, LifeNode.is_deleted.is_(False))


def resolve(value, required=True):
    if value == 'now':
        return None
    if not isinstance(value, str) or ':' not in value:
        raise APIError('脉络节点标识无效。')
    kind, source = value.split(':', 1)
    identifier(source)
    if kind == 'record':
        row = db.session.scalar(record_query().where(LifeRecord.source_id == source))
    elif kind in KINDS:
        row = db.session.scalar(node_query().where(LifeNode.kind == KINDS[kind], LifeNode.source_id == source))
    else:
        raise APIError('脉络节点类型无效。')
    if not row and required:
        raise APIError('这份资料已删除或不属于当前空间。', 404, 'graph_node_unavailable')
    return row


def interval(row):
    if isinstance(row, LifeRecord):
        return window(record_date(row.payload))
    if row.kind != 'chapters':
        return None
    native = row.payload.get('androidDocument', {})
    raw = native.get('eventDate')
    if not raw:
        start, end = row.payload.get('startDate'), row.payload.get('endDate')
        raw = {'precision': 'range' if start and end else 'day' if start else 'unknown', 'start': start, 'end': end}
    return window(event_date(raw))


def projection(row):
    if row is None:
        return {'key': 'now', 'id': 'now', 'type': 'now', 'label': '现在', 'subtitle': graph_today().isoformat(), 'summary': '从此刻出发，慢慢打开与你有关的人与事。', 'version': 0, 'date': None, 'canOpen': False}
    is_record = isinstance(row, LifeRecord)
    kind = 'record' if is_record else row.payload.get('type', 'custom') if row.kind == 'entities' else 'chapter' if row.kind == 'chapters' else 'thread'
    raw_date = record_date(row.payload) if is_record else row.payload.get('androidDocument', {}).get('eventDate')
    return {'key': key(row), 'id': row.source_id, 'type': kind, 'label': row.title or '未命名记录' if is_record else row.name,
            'subtitle': LABELS.get(kind, '对象'), 'summary': (row.content if is_record else row.payload.get('summary', ''))[:280],
            'version': row.version, 'date': raw_date, 'recordState': row.record_state if is_record else None,
            'canOpen': is_record or kind == 'person'}


def filters(args):
    types = set(args.get('types', '').split(',')) - {''} if args.get('types') else TYPES.copy()
    if not types.issubset(TYPES):
        raise APIError('脉络类型筛选无效。')
    bounds = []
    for name in ('from', 'to'):
        raw = args.get(name)
        bounds.append(window(event_date({'precision': 'day', 'start': raw, 'end': None}))[0] if raw else None)
    if all(bounds) and bounds[0] > bounds[1]:
        raise APIError('截止日期不能早于起始日期。')
    return types, bounds


def matches(row, selection):
    types, (lower, upper) = selection
    if projection(row)['type'] not in types:
        return False
    span = interval(row)
    if isinstance(row, LifeRecord) or row.kind == 'chapters':
        if lower and (not span or span[1] < lower) or upper and (not span or span[0] > upper):
            return False
    return True


def temporal(row):
    """只用事件窗口解释“现在”，不把录入/修改时间当经历发生时间。"""
    today = graph_today()
    day = (today.year, today.month, today.day)
    span = interval(row)
    if not isinstance(row, LifeRecord):
        return bool(span and span[0] <= day <= span[1])
    if row.record_state == 'ongoing' and row.payload.get('completionState') not in ('completed', 'cancelled'):
        return True
    lower, upper = today - timedelta(days=30), today + timedelta(days=14)
    return bool(span and span[1] >= (lower.year, lower.month, lower.day) and span[0] <= (upper.year, upper.month, upper.day))


def edge(left, right, temporal_context=False, chapter_context=False):
    a, b = 'now' if left is None else key(left), key(right)
    if temporal_context:
        relation, label = 'time_context', '时间定位 · 非正式关系'
    elif chapter_context:
        relation, label = 'chapter_thread', '阶段关联的长期投入'
    else:
        relation = {'entities': 'record_entity', 'chapters': 'record_chapter', 'threads': 'record_thread'}[right.kind]
        label = {'entities': '记录关联的' + LABELS.get(right.payload.get('type'), '对象'), 'chapters': '归属人生阶段', 'threads': '属于长期投入'}[right.kind]
    return {'id': relation + '|' + a + '|' + b, 'source': a, 'target': b, 'type': relation, 'label': label,
            'provenance': '时间范围或进行中状态，仅用于浏览' if temporal_context else '用户保存的正式关联',
            'editable': not temporal_context and not chapter_context,
            'recordId': left.source_id if isinstance(left, LifeRecord) else None,
            'nodeKey': key(right) if not temporal_context and not chapter_context else None}


def candidates(focus):
    if focus is None:
        # 流式扫描时间候选，不在响应中返回完整事实或整张人生网络。
        for row in db.session.scalars(node_query().where(LifeNode.kind == 'chapters')).yield_per(128):
            if temporal(row):
                yield row, edge(None, row, True)
        for row in db.session.scalars(record_query()).yield_per(128):
            if temporal(row):
                yield row, edge(None, row, True)
    elif isinstance(focus, LifeRecord):
        query = node_query().join(RecordNode, RecordNode.node_id == LifeNode.id).where(RecordNode.record_id == focus.id)
        for node in db.session.scalars(query):
            yield node, edge(focus, node)
    else:
        query = record_query().join(RecordNode, RecordNode.record_id == LifeRecord.id).where(RecordNode.node_id == focus.id)
        for row in db.session.scalars(query).yield_per(128):
            yield row, edge(row, focus)
        # 既有 Android 阶段—长期投入关系从原文读取，不创造第二套边表。
        if focus.kind == 'chapters':
            ids = focus.payload.get('androidDocument', {}).get('threadIds', [])
            if ids:
                for node in db.session.scalars(node_query().where(LifeNode.kind == 'threads', LifeNode.source_id.in_(ids))):
                    yield node, edge(focus, node, chapter_context=True)
        elif focus.kind == 'threads':
            for node in db.session.scalars(node_query().where(LifeNode.kind == 'chapters')).yield_per(128):
                if focus.source_id in node.payload.get('androidDocument', {}).get('threadIds', []):
                    yield node, edge(node, focus, chapter_context=True)


def order(row, focus):
    if focus is not None:
        return (0, key(row))
    rank = 0 if isinstance(row, LifeNode) else 1 if row.record_state == 'ongoing' else 2
    span = interval(row)
    start = span[0] if span else (-1000000000, 1, 1)
    return (rank, -start[0], -start[1], -start[2], key(row))


def neighborhood(args):
    focus_key = args.get('focus', 'now')
    focus = resolve(focus_key)
    selection = filters(args)
    binding = {'owner': g.owner.id, 'focus': focus_key, 'types': sorted(selection[0]), 'bounds': selection[1]}
    signer = URLSafeTimedSerializer(current_app.secret_key, salt='lifegraph-page')
    after = None
    if args.get('cursor'):
        try:
            page = signer.loads(args['cursor'], max_age=900)
            # JSON 序列化会把元组转为列表，统一后再比较。
            import json
            if page['binding'] != json.loads(json.dumps(binding)):
                raise BadSignature('binding')
            after = tuple(page['after'])
        except (BadSignature, KeyError, TypeError, ValueError):
            raise APIError('展开页已过期或不属于当前筛选，请重新展开。', 409, 'graph_cursor_expired') from None
    eligible = ((row, link) for row, link in candidates(focus) if matches(row, selection) and (after is None or order(row, focus) > after))
    page = nsmallest(PAGE + 1, eligible, key=lambda pair: order(pair[0], focus))
    more = len(page) > PAGE
    selected = page[:PAGE]
    nodes = {focus_key: projection(focus)}
    edges = []
    for row, link in selected:
        nodes[key(row)] = projection(row)
        edges.append(link)
    if focus is None:
        # 初始仅补少量直接对象；不递归展开，也不推断人物间关系。
        attached = 0
        for row, _ in selected:
            if not isinstance(row, LifeRecord):
                continue
            for node, link in candidates(row):
                if not matches(node, selection):
                    continue
                if node.kind == 'entities' and key(node) not in nodes and attached < 3:
                    nodes[key(node)] = projection(node)
                    attached += 1
                if key(node) in nodes:
                    edges.append(link)
    cursor = signer.dumps({'binding': binding, 'after': order(selected[-1][0], focus)}) if more else None
    return {'focus': focus_key, 'nodes': list(nodes.values()), 'edges': edges, 'nextCursor': cursor,
            'pageSize': PAGE, 'policy': {'pastDays': 30, 'futureDays': 14, 'contextObjects': 3}}


def snapshot(keys):
    if not isinstance(keys, list) or not 1 <= len(keys) <= 80 or any(not isinstance(k, str) for k in keys):
        raise APIError('一次最多复核80个可见节点。')
    rows = {}
    for value in dict.fromkeys(keys):
        row = resolve(value, required=False)
        if row is not None or value == 'now':
            rows[value] = row
    links = {}
    for value, row in rows.items():
        if row is None:
            for target_key, target in rows.items():
                if target is not None and temporal(target):
                    link = edge(None, target, True)
                    links[link['id']] = link
        elif isinstance(row, LifeRecord):
            query = node_query().join(RecordNode, RecordNode.node_id == LifeNode.id).where(RecordNode.record_id == row.id)
            for node in db.session.scalars(query):
                if key(node) in rows:
                    link = edge(row, node)
                    links[link['id']] = link
        elif row.kind == 'chapters':
            for source in row.payload.get('androidDocument', {}).get('threadIds', []):
                target = rows.get('thread:' + source)
                if target is not None:
                    link = edge(row, target, chapter_context=True)
                    links[link['id']] = link
    return {'nodes': [projection(row) for row in rows.values()], 'edges': list(links.values())}


def search(args):
    query = args.get('q', '').strip()
    if len(query) > 100:
        raise APIError('查找文字不能超过100字。')
    scope = args.get('scope', 'all')
    if scope not in ('all', 'record', 'target'):
        raise APIError('查找范围无效。')
    records, targets = [], []
    if scope != 'target':
        statement = record_query()
        if query:
            statement = statement.where(LifeRecord.title.contains(query, autoescape=True) | LifeRecord.content.contains(query, autoescape=True))
        records = list(db.session.scalars(statement.order_by(LifeRecord.source_id).limit(13)))
    if scope != 'record':
        statement = node_query()
        if query:
            statement = statement.where(LifeNode.name.contains(query, autoescape=True))
        targets = list(db.session.scalars(statement.order_by(LifeNode.kind, LifeNode.source_id).limit(13)))
    # 记录很多时仍保留人物/对象结果，优先精确名称，再交替呈现两类。
    from itertools import zip_longest
    found = [row for pair in zip_longest(targets, records) for row in pair if row is not None]
    found.sort(key=lambda row: (row.title if isinstance(row, LifeRecord) else row.name).casefold() != query.casefold())
    return {'nodes': [projection(row) for row in found[:12]], 'hasMore': len(found) > 12}


def change_relation(value):
    if value.get('confirmed') is not True:
        raise APIError('请明确确认本次关联变更。')
    record = resolve('record:' + identifier(value.get('recordId')))
    node = resolve(value.get('nodeKey'))
    if not isinstance(node, LifeNode) or value.get('operation') not in ('link', 'unlink'):
        raise APIError('请选择一条记录及其对象、阶段或长期投入，不建立推测关系。')
    version = value.get('version')
    if type(version) is not int or version != record.version:
        raise APIError('记录已变化，请重新查看；原输入和草稿未被覆盖。', 409, 'version_conflict')
    existing = next((item for item in record.links if item.node_id == node.id), None)
    adding = value['operation'] == 'link'
    if bool(existing) == adding:
        return {'record': projection(record), 'changed': False}
    result = db.session.execute(db.update(LifeRecord).where(LifeRecord.id == record.id, LifeRecord.version == version).values(version=version + 1).execution_options(synchronize_session=False))
    if result.rowcount != 1:
        raise APIError('记录已更新，未改变关联。', 409, 'version_conflict')
    if adding:
        record.links.append(RecordNode(node_id=node.id))
    else:
        record.links.remove(existing)
    record.version = version + 1
    record.updated_at = now()
    db.session.flush()
    # 通过同一正式关系读取字段，正文、日期、照片和现有草稿均不改写。
    data = record_data(record)
    payload = {**record.payload, **{field: data[field] for field in ('linkedEntityIds', 'linkedThreadIds', 'linkedChapterIds')}}
    if payload.get('androidDocument'):
        from .android_archive import millis, record_document
        payload['androidDocument'] = {**payload['androidDocument'], 'updatedAt': millis(record.updated_at)}
        record.payload = payload
        payload['androidDocument'] = record_document(record)
    record.payload = payload
    db.session.commit()
    return {'record': projection(record), 'changed': True}
