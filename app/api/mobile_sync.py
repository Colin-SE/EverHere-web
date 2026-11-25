"""Android's versioned album and original transfer protocol."""
import hashlib
from io import BytesIO
from threading import BoundedSemaphore

from flask import Blueprint, current_app, g, jsonify, request, send_file
from sqlalchemy import select
from werkzeug.exceptions import HTTPException

from ..extensions import db
from ..models import LocalSpace
from ..models_workflow import SpaceOwnership
from ..security import APIError, body
from ..services import album_sync, identity
from ..services.record_schema import exact
from .mobile_identity import actor
from .records import make_photo


sync = Blueprint('mobile_sync', __name__, url_prefix='/v1/sync')
assets = Blueprint('mobile_assets', __name__, url_prefix='/v1/assets')
MAX_ORIGINAL = 50 * 1024 * 1024
original_uploads = BoundedSemaphore(2)


def guard(bucket, bound, count):
    identity.enabled()
    if not current_app.config.get('ALBUM_SYNC_ENABLED'):
        identity.fail('sync_service_not_configured', 503)
    if request.headers.get('X-Everhere-Region') != 'cn':
        identity.fail('region_mismatch')
    request.max_content_length = bound
    if request.content_length is not None and request.content_length > bound:
        identity.fail('request_too_large', 413)
    identity.limit(request.remote_addr or 'unknown', bucket, count, 300)


@sync.before_request
def guard_sync():
    guard('sync-http', 2 * 1024 * 1024, 600)


@assets.before_request
def guard_assets():
    guard('original-http', MAX_ORIGINAL, 120)


@sync.errorhandler(APIError)
@assets.errorhandler(APIError)
def api_error(error):
    db.session.rollback()
    code = 'invalid_sync_payload' if error.code == 'validation_error' else error.code
    return jsonify(error=code), error.status


@sync.errorhandler(HTTPException)
@assets.errorhandler(HTTPException)
def http_error(error):
    db.session.rollback()
    return jsonify(error='request_too_large' if error.code == 413 else 'invalid_request'), error.code


def bind(installation):
    installation = identity.uuid(installation)
    if db.engine.dialect.name == 'mysql':
        # The token lookup may precede a lock wait on another request.
        db.session.connection(execution_options={'isolation_level': 'READ COMMITTED'})
    member, device = actor()
    if device.installation_id != installation:
        identity.fail('installation_mismatch', 403)
    owner_id = db.session.scalar(select(SpaceOwnership.space_id).where(
        SpaceOwnership.member_id == member.id,
    ).order_by(SpaceOwnership.space_id).limit(1))
    if owner_id is None:
        identity.fail('album_not_found', 409)
    g.owner = db.session.scalar(select(LocalSpace).where(LocalSpace.id == owner_id).with_for_update())
    if g.owner is None:
        identity.fail('album_not_found', 409)


def commit(result):
    db.session.commit()
    return result


@sync.post('/push')
def push():
    op = album_sync.operation(body())
    bind(op['installationId'])
    return commit(album_sync.push(op))


@sync.post('/pull')
def pull():
    value = exact(body(), ['installationId', 'cursor', 'limit'])
    bind(value['installationId'])
    return commit(album_sync.pull(value['installationId'], value['cursor'], album_sync.page_size(value['limit'])))


@sync.post('/conflicts')
def conflicts():
    value = exact(body(), ['installationId', 'afterId', 'limit'])
    bind(value['installationId'])
    return album_sync.conflicts(value['afterId'], album_sync.page_size(value['limit']))


@sync.post('/resolve')
def resolve():
    value = exact(body(), ['conflictId', 'choice', 'expectedRemoteVersion', 'operation'])
    op = album_sync.operation(value['operation'])
    bind(op['installationId'])
    return commit(album_sync.resolve(value, op))


def authorized_asset(asset_id):
    bind(request.headers.get('X-Everhere-Installation'))
    photo = album_sync.photo_row(asset_id)
    if photo is None:
        identity.fail('asset_not_found', 404)
    mapping, metadata = album_sync.asset_metadata(photo)
    if metadata['byteSize'] is None:
        identity.fail('asset_metadata_incomplete', 409)
    return photo, mapping, metadata


@assets.get('/<asset_id>/original')
def original(asset_id):
    photo, mapping, spec = authorized_asset(asset_id)
    if mapping and not mapping.ready:
        identity.fail('original_not_ready', 409)
    raw = photo.data
    if len(raw) != int(spec['byteSize']) or hashlib.sha256(raw).hexdigest() != spec['sha256']:
        identity.fail('original_integrity_failed', 503)
    response = send_file(BytesIO(raw), mimetype='application/octet-stream', as_attachment=True,
                         download_name='original', conditional=False)
    response.headers['X-Everhere-SHA256'] = spec['sha256']
    return response


@assets.post('/<asset_id>/original')
def upload(asset_id):
    if request.mimetype != 'application/octet-stream':
        identity.fail('invalid_original')
    if not original_uploads.acquire(blocking=False):
        identity.fail('try_later', 429)
    try:
        _, _, spec = authorized_asset(asset_id)
        length = int(spec['byteSize'])
        db.session.rollback()  # Release the database locks while the device sends bytes.
        if request.content_length is not None and request.content_length != length:
            identity.fail('original_integrity_failed')
        raw = request.stream.read(length + 1)
        if len(raw) != length or hashlib.sha256(raw).hexdigest() != spec['sha256']:
            identity.fail('original_integrity_failed')
        photo, mapping, current = authorized_asset(asset_id)
        if current != spec:
            identity.fail('asset_metadata_conflict', 409)
        if mapping and not mapping.ready:
            try:
                verified = make_photo(raw)
                measured = album_sync.photo_metadata(verified)
            except APIError:
                identity.fail('original_integrity_failed')
            for name in ('mimeType', 'width', 'height'):
                if spec[name] is not None and spec[name] != measured[name]:
                    identity.fail('original_integrity_failed')
            photo.data, photo.thumbnail_data = raw, verified.thumbnail_data
            mapping.ready = True
        return commit({'status': 'ready', 'assetId': asset_id, 'sha256': spec['sha256'], 'byteSize': spec['byteSize']})
    finally:
        original_uploads.release()
