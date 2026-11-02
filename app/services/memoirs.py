"""提交材料与审核状态机：不可变素材和可变工作状态分别保存。"""
from copy import deepcopy
from hashlib import sha256

from flask import g
from sqlalchemy import select

from ..extensions import db
from ..models import LifeRecord, Photo, new_id, now
from ..models_workflow import Memoir, MemoirRevision, MemoirAsset
from ..security import APIError
from ..i18n import translate
from .records import record_data, text


def active_revision(memoir):
    return db.session.scalar(select(MemoirRevision).where(MemoirRevision.memoir_id == memoir.id, MemoirRevision.number == memoir.revision_number))


def get_memoir(memoir_id, *, admin=False, lock=False):
    query = select(Memoir).where(Memoir.id == memoir_id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    memoir = db.session.scalar(query)
    if not memoir or (not admin and memoir.owner_id != g.member.id):
        raise APIError('回忆录不存在。', 404, 'not_found')
    return memoir


def check_version(memoir, data, revision=False):
    if type(data.get('version')) is not int or data['version'] != memoir.version:
        raise APIError('回忆录已更新，请刷新后重试；当前输入仍可保留。', 409, 'version_conflict')
    current = active_revision(memoir)
    if revision and (not current or data.get('revisionId') != current.id):
        raise APIError('当前稿件版本已变化，不能处理旧版本。', 409, 'version_conflict')
    return current


def touch(memoir):
    memoir.version += 1
    memoir.updated_at = now()


def assigned(memoir, revision):
    if not revision or revision.reviewer_id != g.member.id or memoir.owner_id == g.member.id:
        raise APIError('只能处理分配给自己的稿件。', 403, 'not_assigned')


def normalise_draft(data):
    title, theme = text(data.get('title'), '回忆录标题', 160), text(data.get('theme'), '主题', 300)
    if not title:
        raise APIError('请填写回忆录标题。', code='title')
    chapters = data.get('chapters', [])
    if not isinstance(chapters, list) or len(chapters) > 20:
        raise APIError('回忆录最多选择 20 条记录。', code='chapters')
    result, seen = [], set()
    for chapter in chapters:
        if not isinstance(chapter, dict) or not isinstance(chapter.get('recordId'), str):
            raise APIError('章节须选择有效记录。', code='chapters')
        source = db.session.scalar(select(LifeRecord).where(LifeRecord.user_id == g.owner.id, LifeRecord.source_id == chapter['recordId'], LifeRecord.is_deleted.is_(False)))
        if not source or source.id in seen:
            raise APIError('记录不存在、重复或不属于当前档案。', code='chapters')
        seen.add(source.id)
        photos = chapter.get('photoUris', [])
        if not isinstance(photos, list) or len(photos) > 10 or any(not isinstance(uri, str) for uri in photos) or len(set(photos)) != len(photos):
            raise APIError('章节照片列表无效。', code='photoUris')
        if any(uri not in source.payload.get('photoUris', []) for uri in photos):
            raise APIError('只能选择该记录内的照片。', code='photoUris')
        if type(chapter.get('version')) is not int:
            raise APIError('请刷新来源记录的版本。', 409, 'source_conflict')
        result.append({'recordId': source.source_id, 'version': chapter['version'], 'heading': text(chapter.get('heading', source.title), '章节标题', 200), 'photoUris': photos})
    return title, theme, result


def freeze(memoir):
    if not memoir.draft:
        raise APIError('请至少选择一条有内容的记录。', code='chapters')
    revision_id, chapters, photos, byte_count, text_count = new_id(), [], {}, 0, 0
    for chapter in memoir.draft:
        source = db.session.scalar(select(LifeRecord).where(LifeRecord.user_id == memoir.space_id, LifeRecord.source_id == chapter['recordId']).with_for_update())
        if not source or source.is_deleted or source.version != chapter['version']:
            raise APIError('来源记录已修改或移入回收站，请重新选择并确认素材。', 409, 'source_conflict')
        value = record_data(source)
        if not chapter['heading'].strip() or (not source.content.strip() and not chapter['photoUris']):
            raise APIError('每章须有标题，并包含正文或照片。', code='chapters')
        text_count += len(source.content)
        if text_count > 100_000:
            raise APIError('本阶段单份回忆录正文总计最多 10 万字。', code='chapters')
        selected = []
        for uri in chapter['photoUris']:
            if uri not in value.get('photoUris', []):
                raise APIError('照片已从来源记录移除，请重新选择。', 409, 'source_conflict')
            photo = db.session.get(Photo, uri.rsplit('/', 1)[-1])
            if not photo or photo.user_id != memoir.space_id:
                raise APIError('所选照片不可用，请重新选择。', code='photoUris')
            if photo.id not in photos:
                byte_count += len(photo.data)
                if byte_count > 64 * 1024 * 1024:
                    raise APIError('提交照片总计最多 64 MiB，请减少选图后重试。', 413, 'photoUris')
                asset = MemoirAsset(id=new_id(), revision_id=revision_id, kind='photo', content_type=photo.content_type, data=photo.data, checksum=sha256(photo.data).hexdigest())
                photos[photo.id] = asset
            selected.append(photos[photo.id].id)
        # 不复制未选择的照片、人物关系或整个原始协议文档，避免扩大授权范围。
        chapters.append({'recordId': source.source_id, 'sourceVersion': source.version, 'heading': chapter['heading'], 'content': source.content,
                         'date': value.get('eventDate'), 'dateEnd': value.get('eventEndAt'), 'datePrecision': value.get('datePrecision'),
                         'recordState': source.record_state, 'placeName': value.get('placeName', ''), 'photoAssetIds': selected})
    revision = MemoirRevision(id=revision_id, memoir_id=memoir.id, number=memoir.revision_number + 1,
                              snapshot={'title': memoir.title, 'theme': memoir.theme, 'chapters': deepcopy(chapters), 'authorised': True})
    db.session.add(revision)
    db.session.flush()
    db.session.add_all(photos.values())
    memoir.revision_number += 1
    memoir.state = 'submitted'
    touch(memoir)
    return revision


def memoir_data(memoir, detail=False, staff=False):
    revision = active_revision(memoir)
    value = {'id': memoir.id, 'title': memoir.title, 'theme': memoir.theme, 'state': memoir.state, 'version': memoir.version,
             'revisionNumber': memoir.revision_number, 'updatedAt': memoir.updated_at.isoformat() + 'Z'}
    if revision:
        if staff:
            # 退回后作者可能继续改草稿；管理员仅获授权读取已提交版本的标题与主题。
            value['title'], value['theme'] = revision.snapshot['title'], revision.snapshot['theme']
        value.update(revisionId=revision.id, reviewerId=revision.reviewer_id, reason=revision.reason, renderError=translate(revision.render_error),
                     layout=revision.layout, previewUrl=f'/api/v1/memoirs/{memoir.id}/preview.pdf' if memoir.state == 'ready' else None)
    if detail:
        if not staff:
            value['chapters'] = memoir.draft
        value['revision'] = {'id': revision.id, 'number': revision.number, 'state': revision.state, 'snapshot': revision.snapshot} if revision else None
        query = select(MemoirRevision).where(MemoirRevision.memoir_id == memoir.id)
        if staff:
            query = query.where(MemoirRevision.reviewer_id == g.member.id)
        value['history'] = [{'number': r.number, 'state': r.state, 'reason': r.reason} for r in db.session.scalars(query.order_by(MemoirRevision.number))]
    return value
