"""Flask 应用工厂：扩展、蓝图、页面和统一异常边界。"""

import os
from pathlib import Path
from uuid import uuid4

from flask import Flask, g, jsonify, redirect, render_template, request, url_for
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.exceptions import HTTPException

from .config import settings
from .extensions import db, limiter, migrate, login_manager
from .security import APIError, load_user
from .i18n import error_message, translate, ui_locale
from flask import session


def create_app(test_config=None):
    app = Flask(__name__)
    # 静态图片等并发响应不得刷新旧 Cookie，覆盖刚建立的身份或 CSRF。
    # 动态请求由 load_user 显式更新永久会话，保持七天活动期限。
    app.config['SESSION_REFRESH_EACH_REQUEST'] = False
    if test_config is None:
        app.config.update(settings())
    else:
        app.config.update(SECRET_KEY="tests-only", SQLALCHEMY_DATABASE_URI=os.environ.get('TEST_DATABASE_URL'), TESTING=True, RATELIMIT_ENABLED=False)
        app.config.update(test_config)
    try:
        mysql_configured = make_url(app.config.get('SQLALCHEMY_DATABASE_URI')).get_backend_name() == 'mysql'
    except Exception:
        mysql_configured = False
    if not mysql_configured:
        raise RuntimeError('所有运行及验收环境必须明确配置独立命名的 MySQL 数据库。')
    if app.config.get('SHARED_IDENTITY_ENABLED'):
        import re
        if not re.fullmatch(r'[a-fA-F0-9]{64}', app.config.get('IDENTITY_SECRET', '')):
            raise RuntimeError('共用身份需要独立的 32 字节 IDENTITY_SECRET（十六进制）。')
        if app.config.get('IDENTITY_SMTP_TLS', 'implicit') not in ('implicit', 'starttls'):
            raise RuntimeError('SMTP 必须使用 implicit TLS 或 STARTTLS。')
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    if app.config.get('TRUST_LOOPBACK_PROXY'):
        from .proxy import LoopbackProxy
        app.wsgi_app = LoopbackProxy(app.wsgi_app)
    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)
    login_manager.init_app(app)
    from .models_workflow import Member
    from . import models_identity, models_sync, models_trade
    from .services.alipay import Alipay, GATEWAYS
    mode = app.config.get('ALIPAY_MODE', 'disabled')
    if mode != 'disabled':
        if mode not in GATEWAYS:
            raise RuntimeError('支付宝环境须为 disabled、sandbox 或 production。')
        app.extensions['everhere_alipay'] = Alipay(app.config)

    @login_manager.user_loader
    def member_loader(member_id):
        member = db.session.get(Member, member_id)
        if member and session.get('auth_epoch', 0) == member.auth_epoch:
            return member
        return None
    from .api import auth, drafts, graph, records, accounts, memoirs, shop, order_processing, connections, home, payments
    for blueprint in (auth.bp, records.bp, graph.bp, drafts.bp, accounts.bp, memoirs.bp, shop.bp,
                      order_processing.bp, connections.bp, home.bp, payments.bp):
        app.register_blueprint(blueprint)
    from .api.mobile_identity import bp as mobile_identity_bp
    app.register_blueprint(mobile_identity_bp)
    from .api.mobile_sync import assets, sync
    app.register_blueprint(sync)
    app.register_blueprint(assets)
    app.before_request(load_user)

    @app.context_processor
    def language_context():
        return {'_': translate, 'ui_locale': ui_locale()}

    @app.get('/album')
    @app.get('/places')
    @app.get('/connections')
    @app.get('/records/<source_id>')
    @app.get("/")
    def index(source_id=None):
        view = {'/album': 'timeline', '/places': 'places', '/connections': 'connections'}.get(request.path, 'home')
        if source_id is not None:
            view = 'timeline'
        return render_template("index.html", user=g.user or {"name": translate("本机档案")},
                               initial_view=view, record_id=source_id)

    @app.get("/login")
    def login():
        return redirect(url_for("workspace") + '#account')

    @app.get('/account')
    @app.get('/memoirs')
    @app.get('/memoirs/<item_id>')
    @app.get('/shop')
    @app.get('/shop/products/<item_id>')
    @app.get('/orders')
    @app.get('/orders/<item_id>')
    @app.get('/admin')
    @app.get('/admin/memoirs')
    @app.get('/admin/products')
    @app.get('/admin/orders')
    @app.get('/admin/orders/<item_id>')
    @app.get('/workspace')
    def workspace(item_id=None):
        path = request.path.removesuffix('/' + item_id) if item_id else request.path
        tab = {'/shop/products': 'product', '/admin/memoirs': 'admin-memoirs',
               '/admin/products': 'admin-products', '/admin/orders': 'admin-orders'}.get(path, path[1:])
        return render_template('workspace.html', initial_tab=tab, item_id=item_id)

    from .cli import register_commands
    register_commands(app)

    @app.get("/health")
    def health():
        try:
            db.session.execute(text("SELECT 1"))
        except SQLAlchemyError:
            db.session.rollback()
            return {"status": "unavailable"}, 503
        return {"status": "ok", "database": db.engine.dialect.name}

    @app.after_request
    def secure_headers(response):
        response.headers['Content-Language'] = ui_locale()
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' blob: data:; style-src 'self'; script-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
        if not request.path.startswith('/static/'):
            response.headers["Cache-Control"] = "no-store, private"
        return response

    @app.errorhandler(APIError)
    def api_error(error):
        db.session.rollback()
        return jsonify(error={"code": error.code, "message": error_message(error.message)}), error.status

    @app.errorhandler(IntegrityError)
    def conflict(error):
        db.session.rollback()
        if request.path.startswith('/v1/'):
            return jsonify(error='account_exists'), 409
        return jsonify(error={"code": "conflict", "message": translate("数据已存在或已被修改，请刷新后重试。")}), 409

    @app.errorhandler(SQLAlchemyError)
    def database_error(error):
        db.session.rollback()
        # 不记录 SQL 参数，避免日记正文与密码进入日志。
        reference = uuid4().hex[:12]
        app.logger.error("数据库操作失败 %s：%s", reference, type(error).__name__)
        if request.path.startswith('/v1/'):
            return jsonify(error='temporarily_unavailable'), 503
        return jsonify(error={"code": "database_unavailable", "message": translate("暂时无法保存或读取数据，请稍后重试。"), "reference": reference}), 503

    @app.errorhandler(500)
    def server_error(error):
        reference = uuid4().hex[:12]
        app.logger.error("服务异常 %s：%s", reference, type(error.original_exception).__name__)
        return jsonify(error={"code": "server_error", "message": translate("请求无法完成。"), "reference": reference}), 500

    @app.errorhandler(HTTPException)
    def http_error(error):
        messages = {413: "文件过大，请缩小后重试。", 429: "尝试过于频繁，请稍后再试。", 404: "页面或资源不存在。", 405: "请求方法不支持。"}
        return jsonify(error={"code": str(error.code), "message": translate(messages.get(error.code, "请求无法完成。"))}), error.code

    return app
