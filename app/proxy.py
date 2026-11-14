"""只允许已明确配置的本机 Nginx 影响客户端 IP；外部直连忽略转发头。"""
from ipaddress import ip_address
from werkzeug.middleware.proxy_fix import ProxyFix


class LoopbackProxy:
    def __init__(self, app):
        self.app = app
        self.forwarded = ProxyFix(app, x_for=1, x_proto=1)

    def __call__(self, environ, start_response):
        try:
            trusted = ip_address(environ.get('REMOTE_ADDR', '')).is_loopback
        except ValueError:
            trusted = False
        return (self.forwarded if trusted else self.app)(environ, start_response)
