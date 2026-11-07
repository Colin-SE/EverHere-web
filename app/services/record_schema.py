"""记录日期与旧元数据校验；不提供归档解析、导入或导出。"""
import math
import re
from copy import deepcopy

from app.security import APIError

SHARED = ['type','id','createdAt','updatedAt','deletedAt']
FIELDS = {
 'record': ['title','content','recordState','completionState','eventDate','timezone','placeName','coordinates','tags','mood','showInTimeline','showOnGlobe','privacy','entityIds','threadIds','chapterIds','photos'],
 'entity': ['kind','name','meaning'], 'thread': ['title'], 'chapter': ['title','eventDate','threadIds']}
PHOTO = ['id','mimeType','sha256','byteSize','width','height']


def fail(message='Android 资料格式无效，原文件未改动。'):
    raise APIError(message)


def exact(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys):
        fail('Android 资料含缺失或不支持的字段，请保留原文件并升级适配器。')
    return {key: value[key] for key in keys}


def int64(value, minimum=-(2**63)):
    if not isinstance(value, str) or not re.fullmatch(r'-?(0|[1-9][0-9]{0,18})', value) or not minimum <= int(value) < 2**63 or str(int(value)) != value:
        fail('跨端版本和审计时间必须是精确的 int64 十进制字符串。')
    return value


def text(value, nullable=False, maximum=524288):
    if nullable and value is None:
        return value
    if not isinstance(value, str) or '\x00' in value:
        fail()
    try:
        if len(value.encode('utf-8')) > maximum:
            fail('Android 文字字段超出协议上限。')
    except UnicodeEncodeError:
        fail()
    return value


def identifier(value):
    if not text(value, maximum=1024).strip():
        fail()
    return value


def links(value):
    if not isinstance(value, list) or len(value) > 4096 or any(identifier(x) != x for x in value) or len(set(value)) != len(value):
        fail('Android 关联 ID 无效或重复。')
    return sorted(value)


def event_date(value):
    value = exact(value, ['precision','start','end'])
    def parts(raw, precision):
        if not isinstance(raw, str):
            fail('事件日期无效。')
        if precision == 'year' and re.fullmatch(r'[+-]?[0-9]{1,9}', raw):
            return int(raw), 1, 1
        year = r'([0-9]{4}|-[0-9]{4,10}|\+[0-9]{5,10})'
        pattern = year + (r'-([0-9]{2})' if precision != 'year' else '') + (r'-([0-9]{2})' if precision == 'day' else '')
        match = re.fullmatch(pattern, raw)
        if not match:
            fail('事件日期与精度不匹配。')
        numbers = [int(x) for x in match.groups()]
        y, m, d = (numbers + [1,1])[:3]
        if abs(y)>999999999 or (y==0 and raw.startswith('-')) or not 1<=m<=12:
            fail()
        leap = y%4==0 and (y%100!=0 or y%400==0)
        if not 1<=d<=[31,29 if leap else 28,31,30,31,30,31,31,30,31,30,31][m-1]:
            fail()
        return y,m,d
    precision = value['precision']
    if precision == 'unknown':
        if value['start'] is not None or value['end'] is not None:
            fail()
    elif precision in ('year','month','day'):
        parts(value['start'], precision)
        if value['end'] is not None:
            fail()
    elif precision == 'range':
        if parts(value['start'],'day') > parts(value['end'],'day'):
            fail()
    else:
        fail()
    return value


def document(raw):
    if not isinstance(raw, dict) or raw.get('type') not in FIELDS:
        fail('不支持的 Android 资料类型。')
    kind = raw['type']; value = exact(raw, SHARED+FIELDS[kind])
    identifier(value['id'])
    for key in ('createdAt','updatedAt','deletedAt'):
        if key != 'deletedAt' or value[key] is not None:
            int64(value[key])
    if kind in ('record','chapter'):
        value['eventDate'] = event_date(value['eventDate'])
    for key in ('title','content','name','meaning','timezone'):
        if key in value:
            text(value[key])
    if kind == 'entity' and value['kind'] not in ('person','pet','place','work','media','object','custom'):
        fail()
    if kind == 'entity' and not value['name'].strip() or kind in ('chapter','thread') and not value['title'].strip():
        fail()
    for key in ('entityIds','threadIds','chapterIds'):
        if key in value:
            value[key] = links(value[key])
    if kind != 'record':
        return value
    if value['privacy'] != 'standard':
        fail('保险箱资料默认仅保存在原端，此入口拒绝导入受保护内容。')
    if value['recordState'] not in ('occurred','ongoing','planned','recurring') or value['completionState'] not in ('planned','started','completed','cancelled'):
        fail()
    if not value['title'].strip() and not value['content'].strip():
        fail()
    if not isinstance(value['tags'], list) or len(value['tags'])>1024:
        fail()
    for tag in value['tags']:
        text(tag, maximum=1024)
    for key in ('placeName','mood'):
        text(value[key], nullable=True, maximum=8192)
    for key in ('showInTimeline','showOnGlobe'):
        if type(value[key]) is not bool:
            fail()
    point = value['coordinates']
    if point is not None:
        point=exact(point, ['latitude','longitude','precision']); value['coordinates']=point
        if point['precision'] not in ('gps','city','region'):
            fail()
        for key, limit in [('latitude',90),('longitude',180)]:
            n=point[key]
            if type(n) not in (float,int) or not math.isfinite(n) or abs(n)>limit:
                fail()
    if not isinstance(value['photos'],list) or len(value['photos'])>10:
        fail()
    photos=[]
    for photo in value['photos']:
        photo=exact(photo,PHOTO); identifier(photo['id'])
        if not re.fullmatch('image/[A-Za-z0-9.+-]+',text(photo['mimeType'])) or not re.fullmatch('[a-f0-9]{64}',text(photo['sha256'])):
            fail()
        if photo['byteSize'] is not None and int(int64(photo['byteSize'],1))>50*1024*1024:
            fail()
        for key in ('width','height'):
            n=photo[key]
            if n is not None and (type(n) not in (int,float) or n!=int(n) or not 1<=n<=100000000):
                fail()
        if photo['width'] and photo['height'] and photo['width']*photo['height']>100000000:
            fail()
        photos.append(photo)
    if len({p['id'] for p in photos})!=len(photos):
        fail()
    value['photos']=photos
    return value
