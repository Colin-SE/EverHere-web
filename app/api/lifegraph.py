"""人生脉络的局部读取、授权复核与显式关联编辑。"""
from flask import Blueprint, request
from ..security import body, local_required
from ..services.lifegraph import neighborhood, snapshot, search, change_relation

bp = Blueprint('lifegraph', __name__, url_prefix='/api/v1/lifegraph')


@bp.get('/neighbors')
@local_required
def neighbors():
    return {'data': neighborhood(request.args)}


@bp.post('/snapshot')
@local_required
def refresh():
    return {'data': snapshot(body().get('keys'))}


@bp.get('/search')
@local_required
def find():
    return {'data': search(request.args)}


@bp.post('/relations')
@local_required
def relate():
    return {'data': change_relation(body())}
