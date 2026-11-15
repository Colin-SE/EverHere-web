"""支付宝开放平台经典网关，使用 RSA2 请求签名及响应/通知验签。"""
import base64
import binascii
import json
import re
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from zoneinfo import ZoneInfo

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

SHANGHAI = ZoneInfo('Asia/Shanghai')
GATEWAYS = {
    'sandbox': 'https://openapi-sandbox.dl.alipaydev.com/gateway.do',
    'production': 'https://openapi.alipay.com/gateway.do',
}
SANDBOX_GATEWAYS = {GATEWAYS['sandbox'], 'https://openapi.alipaydev.com/gateway.do'}


class AlipayError(Exception):
    """网络结果不确定、渠道拒绝或验签失败。"""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def payload(fields, excluded=()):
    return '&'.join(f'{key}={value}' for key, value in sorted(fields.items())
                    if key not in excluded and value not in ('', None)).encode('utf-8')


def pem(path, label):
    value = Path(path).read_text(encoding='utf-8-sig').strip().encode('ascii')
    if not value.startswith(b'-----BEGIN '):
        value = f'-----BEGIN {label}-----\n'.encode() + value + f'\n-----END {label}-----'.encode()
    return value


def signed_member(raw, name):
    """取出响应成员的原始 JSON 切片。重新序列化会改变支付宝签名覆盖的字节。"""
    decoder = json.JSONDecoder(parse_float=Decimal)
    position = len(raw) - len(raw.lstrip())
    if raw[position:position + 1] != '{':
        raise ValueError('Expected response object')
    position += 1
    values = {}
    while True:
        position += len(raw[position:]) - len(raw[position:].lstrip())
        if raw[position:position + 1] == '}':
            break
        key, position = decoder.raw_decode(raw, position)
        position += len(raw[position:]) - len(raw[position:].lstrip())
        if raw[position:position + 1] != ':' or key in values:
            raise ValueError('Invalid response member')
        position += 1
        position += len(raw[position:]) - len(raw[position:].lstrip())
        start = position
        value, position = decoder.raw_decode(raw, position)
        values[key] = (value, raw[start:position])
        position += len(raw[position:]) - len(raw[position:].lstrip())
        if raw[position:position + 1] == '}':
            break
        if raw[position:position + 1] != ',':
            raise ValueError('Invalid response separator')
        position += 1
    if raw[position + 1:].strip():
        raise ValueError('Unexpected trailing response data')
    return values[name], values['sign'][0]


class Alipay:
    def __init__(self, config):
        self.environment = config.get('ALIPAY_MODE')
        self.gateway = GATEWAYS[self.environment]
        if self.environment == 'sandbox' and config.get('ALIPAY_SANDBOX_GATEWAY'):
            self.gateway = config['ALIPAY_SANDBOX_GATEWAY']
            if self.gateway not in SANDBOX_GATEWAYS:
                raise ValueError('请选择支付宝控制台提供的官方沙箱网关。')
        self.app_id = config.get('ALIPAY_APP_ID', '')
        self.seller_id = config.get('ALIPAY_SELLER_ID', '')
        self.origin = config.get('ALIPAY_PUBLIC_ORIGIN', '').rstrip('/')
        origin = urlsplit(self.origin)
        if (origin.scheme != 'https' or not origin.hostname or origin.username or origin.password
                or origin.path or origin.query or origin.fragment or not re.fullmatch(r'[0-9]{10,32}', self.app_id)
                or not re.fullmatch(r'[0-9]{10,32}', self.seller_id)):
            raise ValueError('支付宝需要有效应用 ID、卖家 PID 与 HTTPS 公网 origin。')
        self.private_key = serialization.load_pem_private_key(pem(config['ALIPAY_PRIVATE_KEY_FILE'], 'PRIVATE KEY'), None)
        self.public_key = serialization.load_pem_public_key(pem(config['ALIPAY_PUBLIC_KEY_FILE'], 'PUBLIC KEY'))
        if (not isinstance(self.private_key, rsa.RSAPrivateKey) or self.private_key.key_size < 2048
                or not isinstance(self.public_key, rsa.RSAPublicKey) or self.public_key.key_size < 2048):
            raise ValueError('支付宝 RSA2 密钥至少 2048 位。')
        if self.private_key.public_key().public_numbers() == self.public_key.public_numbers():
            raise ValueError('支付宝公钥应由沙箱或正式控制台提供。')
        self.http = build_opener(NoRedirect())

    def request_fields(self, method, biz, **urls):
        fields = {
            'app_id': self.app_id, 'method': method, 'format': 'JSON', 'charset': 'utf-8',
            'sign_type': 'RSA2', 'timestamp': datetime.now(SHANGHAI).strftime('%Y-%m-%d %H:%M:%S'),
            'version': '1.0', 'biz_content': json.dumps(biz, ensure_ascii=False, separators=(',', ':')),
            **urls,
        }
        signature = self.private_key.sign(payload(fields), padding.PKCS1v15(), hashes.SHA256())
        return {**fields, 'sign': base64.b64encode(signature).decode('ascii')}

    def verify(self, data, signature):
        try:
            self.public_key.verify(base64.b64decode(signature, validate=True), data, padding.PKCS1v15(), hashes.SHA256())
        except (InvalidSignature, ValueError, TypeError, binascii.Error) as error:
            raise AlipayError('invalid_signature') from error

    def verify_notice(self, fields):
        if fields.get('sign_type') != 'RSA2':
            raise AlipayError('invalid_signature_type')
        self.verify(payload(fields, ('sign', 'sign_type')), fields.get('sign', ''))

    def checkout_url(self, trade):
        expires = trade.expires_at.replace(tzinfo=timezone.utc).astimezone(SHANGHAI)
        fields = self.request_fields('alipay.trade.page.pay', {
            'out_trade_no': trade.merchant_no, 'total_amount': cents_amount(trade.amount_cents),
            'subject': 'Everhere 在场纪念商城', 'product_code': 'FAST_INSTANT_TRADE_PAY',
            'time_expire': expires.strftime('%Y-%m-%d %H:%M:%S'),
        }, notify_url=self.origin + '/payments/alipay/notify',
            return_url=self.origin + '/orders/' + trade.order_id)
        return self.gateway + '?' + urlencode(fields)

    def call(self, method, biz):
        request = Request(self.gateway, data=urlencode(self.request_fields(method, biz)).encode('ascii'),
                          headers={'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'})
        try:
            with self.http.open(request, timeout=10) as response:
                raw = response.read(262145)
            if len(raw) > 262144:
                raise ValueError('Oversized response')
            (result, original), signature = signed_member(raw.decode('utf-8'), method.replace('.', '_') + '_response')
            self.verify(original.encode('utf-8'), signature)
            if not isinstance(result, dict):
                raise ValueError('Invalid response')
            return result
        except (OSError, URLError, KeyError, ValueError, TypeError) as error:
            raise AlipayError('unconfirmed_gateway_response') from error


def cents_amount(cents):
    return f'{cents // 100}.{cents % 100:02d}'


def amount_cents(value):
    if type(value) is int or isinstance(value, Decimal):
        value = str(value)
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{1,10}(?:\.[0-9]{1,2})?', value):
        raise AlipayError('invalid_amount')
    yuan, _, fraction = value.partition('.')
    return int(yuan) * 100 + int(fraction.ljust(2, '0'))
