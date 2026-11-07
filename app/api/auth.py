"""F1—F4 共用网站身份与 CSRF，不读取已停用的云凭证。"""
from flask import Blueprint, g
from ..security import csrf_token

bp = Blueprint('auth', __name__, url_prefix='/api/v1/auth')


@bp.get('/session')
def current():
    return {'data': {'user': g.user, 'member': g.user, 'csrfToken': csrf_token()}}
