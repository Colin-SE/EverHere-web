"""专用合成浏览器检查服务；不读生产配置，不向真实邮箱发信。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from app.extensions import db
from flask import request

mailbox = {}
application = create_app({
    'SQLALCHEMY_DATABASE_URI': 'sqlite://', 'SESSION_COOKIE_SECURE': False,
    'SHARED_IDENTITY_ENABLED': True, 'IDENTITY_SECRET': 'ac' * 32,
    'IDENTITY_TEST_MAILER': lambda address, purpose, code: mailbox.update({(address, purpose): code}),
})
with application.app_context():
    db.create_all()


@application.get('/__test/code')
def code():
    return {'code': mailbox.get((request.args.get('email'), request.args.get('purpose')))}


if __name__ == '__main__':
    application.run(host='127.0.0.1', port=5017, debug=False, threaded=False, use_reloader=False)
