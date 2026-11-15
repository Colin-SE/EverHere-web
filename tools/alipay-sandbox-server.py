"""本机支付宝沙箱服务。独立数据库、访问口令和沙箱配置均位于项目 tmp 目录。"""
import base64
import hmac
import json
import secrets
import sys
from threading import Thread
from time import sleep
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from flask_migrate import upgrade
from waitress import serve
from werkzeug.wrappers import Response

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import create_app
from app.extensions import db
from app.models_workflow import Member, Product, ProductVariant
from app.services.commerce import expire_overdue

STATE = ROOT / 'tmp' / 'alipay-p4'
ADMIN = 'p4-admin@example.test'


def write_new(path, value):
    if not path.exists():
        with path.open('x', encoding='utf-8') as output:
            output.write(value)


def prepare():
    STATE.mkdir(parents=True, exist_ok=True)
    access_file = STATE / 'test-access.json'
    write_new(access_file, json.dumps({'entranceUser': 'everhere-test', 'entrancePassword': secrets.token_urlsafe(24),
                                       'adminEmail': ADMIN, 'adminPassword': secrets.token_urlsafe(24),
                                       'sessionKey': secrets.token_hex(32)}, indent=2))
    write_new(STATE / 'settings.json', json.dumps({'appId': '', 'sellerId': '', 'sandboxGateway': ''}, indent=2))
    private = STATE / 'merchant-private.pem'
    if not private.exists():
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        write_new(private, key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                            serialization.NoEncryption()).decode('ascii'))
    key = serialization.load_pem_private_key(private.read_bytes(), None)
    public = key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    write_new(STATE / 'upload-this-app-public-key.txt', base64.b64encode(public).decode('ascii') + '\n')


def payment_config():
    settings = json.loads((STATE / 'settings.json').read_text(encoding='utf-8-sig'))
    origin_file = STATE / 'origin.txt'
    origin = origin_file.read_text(encoding='utf-8-sig').strip() if origin_file.exists() else ''
    public = STATE / 'alipay-public.pem'
    if not (str(settings.get('appId', '')).strip() and str(settings.get('sellerId', '')).strip() and public.exists() and origin):
        return {}
    return {'ALIPAY_MODE': 'sandbox', 'ALIPAY_PUBLIC_ORIGIN': origin,
            'ALIPAY_SANDBOX_GATEWAY': str(settings.get('sandboxGateway', '')).strip(),
            'ALIPAY_APP_ID': str(settings['appId']).strip(), 'ALIPAY_SELLER_ID': str(settings['sellerId']).strip(),
            'ALIPAY_PRIVATE_KEY_FILE': str(STATE / 'merchant-private.pem'), 'ALIPAY_PUBLIC_KEY_FILE': str(public)}


def seed(application, credentials):
    with application.app_context():
        upgrade(directory=str(ROOT / 'migrations'))
        if not db.session.query(Member).filter_by(email=ADMIN).first():
            response = application.test_cli_runner().invoke(args=['create-admin', '--email', ADMIN,
                '--name', 'P4 Sandbox Administrator', '--password', credentials['adminPassword']])
            if response.exit_code:
                raise RuntimeError('无法建立沙箱管理员')
        if not db.session.query(Product).first():
            product = Product(name='P4 沙箱测试纪念牌', description='测试商品，付款和退款使用支付宝沙箱余额。', active=True)
            db.session.add(product)
            db.session.flush()
            db.session.add(ProductVariant(product_id=product.id, name='沙箱测试款', kind='medal', price_cents=100,
                                          stock_available=12, text_required=False))
            db.session.commit()


def require_entry(app, credentials):
    secret = credentials['entranceUser'] + ':' + credentials['entrancePassword']
    expected = 'Basic ' + base64.b64encode(secret.encode()).decode('ascii')

    def gated(environ, send):
        path = environ.get('PATH_INFO', '')
        method = environ.get('REQUEST_METHOD')
        if path == '/payments/alipay/notify' and method == 'POST' or path == '/health' and method in ('GET', 'HEAD'):
            return app(environ, send)
        if hmac.compare_digest(environ.get('HTTP_AUTHORIZATION', '').encode(), expected.encode()):
            return app(environ, send)
        return Response('Everhere Alipay Sandbox', status=401,
                        headers={'WWW-Authenticate': 'Basic realm="Everhere P4 Sandbox"', 'Cache-Control': 'no-store'})(environ, send)
    return gated


def main():
    prepare()
    if '--prepare' in sys.argv:
        print('Sandbox configuration and application public key are ready.')
        return
    credentials = json.loads((STATE / 'test-access.json').read_text(encoding='utf-8-sig'))
    payment = payment_config()
    application = create_app({'SECRET_KEY': credentials['sessionKey'], 'SQLALCHEMY_DATABASE_URI': 'sqlite:///' +
        (STATE / 'sandbox.sqlite3').as_posix(), 'TESTING': False, 'SESSION_COOKIE_SECURE': True,
        'RATELIMIT_ENABLED': True, 'MAX_CONTENT_LENGTH': 16 * 1024 * 1024, **payment})
    seed(application, credentials)
    if payment:
        def close_expired():
            while True:
                sleep(30)
                try:
                    with application.app_context():
                        expire_overdue()
                except Exception as error:
                    application.logger.error('沙箱超时关单中断：%s', type(error).__name__)
        Thread(target=close_expired, daemon=True, name='sandbox-expiry').start()
    print('Everhere P4 sandbox ready on 127.0.0.1:15044; Alipay ' + ('configured' if payment else 'awaiting configuration'), flush=True)
    serve(require_entry(application, credentials), listen='127.0.0.1:15044', threads=6,
          max_request_body_size=16 * 1024 * 1024)


if __name__ == '__main__':
    main()
