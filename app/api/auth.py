"""浏览器会话只绑定本机空间；账户身份来自共同云服务。"""
from flask import Blueprint, current_app, g

from ..extensions import db
from ..models import CloudConnection
from ..security import csrf_token

bp = Blueprint('auth', __name__, url_prefix='/api/v1/auth')


@bp.get('/session')
def current():
    connection = db.session.get(CloudConnection, g.owner.id)
    user = {'id': connection.account_id, 'name': connection.email.split('@')[0], 'email': connection.email} if connection else None
    return {'data': {'user': user, 'csrfToken': csrf_token(), 'region': current_app.config.get('CLOUD_REGION', 'cn'), 'cloudConfigured': bool(current_app.config.get('CLOUD_API_URL'))}}
