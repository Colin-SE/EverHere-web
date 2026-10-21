"""共享记录校验、查询和关系编排，不依赖具体前端视图。"""

import math
import re
from datetime import date, datetime, timezone
from uuid import uuid4

from flask import g
from sqlalchemy import or_, select

from ..extensions import db
from ..models import LifeNode, LifeRecord, Photo, RecordNode, now
from ..security import APIError

KINDS = {"entities": "linkedEntityIds", "threads": "linkedThreadIds", "chapters": "linkedChapterIds"}
STATES = {"occurred", "ongoing", "planned", "recurring"}


def enum_value(value, allowed, label):
    if not isinstance(value, str) or value not in allowed:
        raise APIError(f"{label}无效。")
    return value


def text(value, field, limit=200, default=""):
    if value is None:
        value = default
    if not isinstance(value, str) or len(value) > limit:
        raise APIError(f"{field}须为不超过 {limit} 字的文字。")
    return value.strip()


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", value):
        raise APIError("ID 格式无效。")
    return value


def date_value(value, label):
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise APIError(f"{label}格式无效。")
    try:
        if len(value) != 10:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        return date.fromisoformat(value[:10])
    except (ValueError, TypeError):
        raise APIError(f"{label}须为有效日期。") from None


def string_list(value, label, max_items=50, max_length=100):
    if not isinstance(value, list) or len(value) > max_items:
        raise APIError(f"{label}须为最多 {max_items} 项的列表。")
    return list(dict.fromkeys(text(item, label, max_length) for item in value if item != ""))


def archive_timestamp(value, label):
    if value is None:
        return None
    if not isinstance(value, str):
        raise APIError(f"{label}格式无效。")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed
    except ValueError:
        raise APIError(f"{label}格式无效。") from None


def normalize_record(raw, importing=False):
    if not isinstance(raw, dict):
        raise APIError("人生记录必须是对象。")
    if raw.get("isPrivate") not in (None, False) or raw.get("privacy", "standard") != "standard":
        raise APIError("当前只支持普通资料；旧保险箱功能已删除。")
    if importing and raw.get("androidDocument") is not None:
        from sync_contract import document
        native = document(raw["androidDocument"])
        if native["type"] != "record" or native["id"] != raw.get("id"):
            raise APIError("Android 资料标识不一致。")
        # 只作现有视图投影，原日期/时区/重复标签/毫秒字符串完整留在同一行。
        text(native["title"], "标题", 200)
        text(native["content"], "正文", 100000)
        from sync_contract import native_projection
        result = native_projection({"documents": [native]})["records"][0]
        result["source"] = "android"
        return result
    if importing:
        archive_timestamp(raw.get("createdAt"), "原创建时间")
        archive_timestamp(raw.get("updatedAt"), "原修改时间")
    result = dict(raw) if importing else {}
    result["title"] = text(raw.get("title", ""), "标题")
    result["content"] = raw.get("content", "")
    text(result["content"], "正文", 100000)
    if not result["title"] and not result["content"].strip():
        raise APIError("请至少写下标题或正文。")
    result["recordState"] = enum_value(raw.get("recordState", "occurred"), STATES, "记录状态")
    defaults = {"occurred": "completed", "ongoing": "started", "planned": "planned", "recurring": "started"}
    result["completionState"] = raw.get("completionState", defaults[result["recordState"]])
    enum_value(result["completionState"], {"planned", "started", "completed", "cancelled"}, "完成状态")
    from .record_query import record_date
    event = record_date(raw)
    result["eventStartAt"] = event["start"]
    result["eventDate"] = event["start"]
    result["eventEndAt"] = event["end"]
    result["datePrecision"] = event["precision"]
    result["timezone"] = text(raw.get("timezone", "Asia/Shanghai"), "事件时区", 256)
    if not result["timezone"]:
        raise APIError("事件时区不能为空。")
    result["placePrecision"] = enum_value(raw.get("placePrecision") or "city", {"gps", "city", "region"}, "地点精度")
    for key, limit in (("placeName", 200), ("mood", 40)):
        result[key] = text(raw.get(key, ""), key, limit)
    for key, limit in (("latitude", 90), ("longitude", 180)):
        value = raw.get(key)
        if value is not None and (isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or abs(value) > limit):
            raise APIError("经纬度须为范围内的有效数字。")
        result[key] = value
    if (result["latitude"] is None) != (result["longitude"] is None):
        raise APIError("经度和纬度需要同时填写。")
    tags = raw.get("tags", [])
    if not isinstance(tags, list) or len(tags) > 1024:
        raise APIError("标签须为最多 1024 项的列表。")
    for tag in tags:
        text(tag, "标签", 1024)
    result["tags"] = list(tags)
    result["photoUris"] = string_list(raw.get("photoUris", []), "照片", 10, 1000)
    for key in KINDS.values():
        result[key] = [identifier(item) for item in string_list(raw.get(key, []), key)]
    for key, default in (("showInTimeline", True), ("showOnGlobe", False)):
        value = raw.get(key, default)
        if type(value) is not bool:
            raise APIError(f"{key} 须为布尔值。")
        result[key] = value
    result.pop("isPrivate", None)
    result["privacy"] = "standard"
    result["source"] = "imported" if importing else "manual"
    return result


def record_data(record):
    value = dict(record.payload)
    value.update(id=record.source_id, title=record.title, content=record.content,
                 recordState=record.record_state, privacy=record.privacy, isDeleted=record.is_deleted,
                 version=record.version, createdAt=record.created_at.isoformat() + "Z",
                 updatedAt=record.updated_at.isoformat() + "Z")
    for kind, field in KINDS.items():
        value[field] = [link.node.source_id for link in record.links if link.node.kind == kind]
    return value


def owned_record(source_id, include_deleted=False):
    record = db.session.scalar(select(LifeRecord).where(LifeRecord.user_id == g.owner.id, LifeRecord.source_id == source_id))
    if not record or (record.is_deleted and not include_deleted):
        raise APIError("记录不存在。", 404, "not_found")
    return record


def validate_photos(uris, importing, previous=None):
    for uri in uris:
        if previous and uri in previous:
            continue
        if uri.startswith("/api/v1/photos/"):
            photo = db.session.get(Photo, uri.rsplit("/", 1)[-1])
            if not photo or photo.user_id != g.owner.id:
                if importing:
                    # 保留外部引用，前端不会自动请求导入的远程资源。
                    continue
                raise APIError("照片不存在或不属于当前用户。")
        elif not importing:
            raise APIError("请使用本应用上传的照片。")


def save_record(raw, record=None, importing=False, source_id=None):
    previous = dict(record.payload) if record else {}
    if record and record.is_deleted:
        raise APIError("记录已移入回收站，请先恢复，编辑内容仍可保留为草稿。", 409, "record_deleted")
    merged = {**previous, **raw} if not importing else raw
    value = normalize_record(merged, importing)
    if record and record.record_state == "planned" and value["recordState"] == "occurred":
        if raw.get("actualDateConfirmed") is not True or value["datePrecision"] == "unknown":
            raise APIError("计划转为已发生时，请补充并明确确认实际发生日期。", 409, "actual_date_required")
    validate_photos(value["photoUris"], importing, record.payload.get("photoUris", []) if record else None)
    nodes = []
    for kind, field in KINDS.items():
        for node_id in value[field]:
            node = db.session.scalar(select(LifeNode).where(LifeNode.user_id == g.owner.id, LifeNode.kind == kind, LifeNode.source_id == node_id, True if importing else LifeNode.is_deleted.is_(False)))
            if not node:
                raise APIError("记录引用了不存在的对象、线索或阶段。")
            nodes.append(node)
    if record is None:
        record = LifeRecord(user_id=g.owner.id, source_id=source_id or str(uuid4()))
        if importing:
            record.created_at = archive_timestamp(raw.get("createdAt"), "原创建时间") or now()
            record.updated_at = archive_timestamp(raw.get("updatedAt"), "原修改时间") or record.created_at
        db.session.add(record)
    else:
        record.version += 1
        record.updated_at = now()
    record.title, record.content = value["title"], value["content"]
    record.record_state, record.privacy = value["recordState"], "standard"
    native = value.get("androidDocument") if importing else previous.get("androidDocument")
    if importing and native:
        record.is_deleted = native["deletedAt"] is not None
    try:
        record.event_date = date.fromisoformat(value["eventStartAt"]) if value["datePrecision"] in ("day", "range") else None
    except (ValueError, TypeError):
        record.event_date = None
    value.pop("androidDocument", None)
    record.payload = {**previous, **value}
    if native:
        from copy import deepcopy
        source = deepcopy(native)
        record.payload = {**record.payload, "androidDocument": source}
        if not importing:
            from .android_archive import record_document, millis
            source["updatedAt"] = millis(record.updated_at)
            # 记录关系重建后再生成文档，不能使用旧关联清单。
    # 先清空关联行，避免同一事务重建关系时违反唯一约束。
    record.links.clear()
    db.session.flush()
    record.links = [RecordNode(node_id=node.id) for node in nodes]
    db.session.flush()
    if native and not importing:
        from .android_archive import record_document
        record.payload = {**record.payload, "androidDocument": record_document(record)}
    return record


def normalize_node(kind, raw):
    if kind not in KINDS or not isinstance(raw, dict):
        raise APIError("人生对象类型无效。")
    value = dict(raw)
    if "linkedRecordIds" in raw:
        string_list(raw["linkedRecordIds"], "关联记录", 5000)
    value["name"] = text(raw.get("name", raw.get("title", "")), "名称", 120)
    if not value["name"]:
        raise APIError("请填写名称。")
    value["summary"] = raw.get("summary", raw.get("description", ""))
    text(value["summary"], "意义", 10000)
    if kind == "entities":
        value["type"] = raw.get("type", "person")
        enum_value(value["type"], {"person", "pet", "place", "work", "media", "object", "custom"}, "对象类型")
    if kind == "threads":
        value["status"] = raw.get("status", "active")
        enum_value(value["status"], {"planned", "active", "paused", "completed", "redirected", "ended"}, "线索状态")
        value["title"], value["description"] = value["name"], value["summary"]
    start = date_value(raw.get("startDate", raw.get("startedOn")), "开始日期")
    end = date_value(raw.get("endDate", raw.get("endedOn")), "结束日期")
    if start and end and end < start:
        raise APIError("结束日期不能早于开始日期。")
    value["startDate"], value["endDate"] = start.isoformat() if start else None, end.isoformat() if end else None
    value.pop("linkedRecordIds", None)
    return value


def node_data(node, visible_ids=None):
    value = dict(node.payload)
    ids = [link.record.source_id for link in node.links if not link.record.is_deleted and (visible_ids is None or link.record.id in visible_ids)]
    value.update(id=node.source_id, name=node.name, version=node.version, linkedRecordIds=ids, recordCount=len(ids), isDeleted=node.is_deleted)
    return value
