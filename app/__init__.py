"""Flask 应用工厂：扩展、蓝图、页面和统一异常边界。"""

from pathlib import Path

from flask import Flask, g, jsonify, redirect, render_template, request, url_for
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.exceptions import HTTPException

from .config import settings
from .extensions import db, limiter, migrate
from .security import APIError, load_user
from .i18n import error_message, translate, ui_locale


@event.listens_for(Engine, "connect")
def sqlite_foreign_keys(connection, _):
    # SQLite 测试环境同样执行外键约束，避免测试掩盖级联删除问题。
    if connection.__class__.__module__.startswith("sqlite3"):
        connection.execute("PRAGMA foreign_keys=ON")


def create_app(test_config=None):
    app = Flask(__name__)
    if test_config is None:
        app.config.update(settings())
    else:
        app.config.update(SECRET_KEY="tests-only", SQLALCHEMY_DATABASE_URI="sqlite://", TESTING=True, RATELIMIT_ENABLED=False)
        app.config.update(test_config)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)
    from .api import archive, auth, cloud, drafts, graph, lifegraph, records
    for blueprint in (auth.bp, records.bp, graph.bp, archive.bp, cloud.bp, drafts.bp, lifegraph.bp):
        app.register_blueprint(blueprint)
    app.before_request(load_user)

    @app.context_processor
    def language_context():
        return {'_': translate, 'ui_locale': ui_locale()}

    @app.get("/")
    def index():
        return render_template("index.html", user=g.user or {"name": translate("本机档案")})

    @app.get("/login")
    def login():
        if g.user:
            return redirect(url_for("index"))
        return render_template("login.html")

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
        if request.path.startswith(("/api/", "/login")) or request.path == "/":
            response.headers["Cache-Control"] = "no-store, private"
        return response

    @app.errorhandler(APIError)
    def api_error(error):
        db.session.rollback()
        return jsonify(error={"code": error.code, "message": error_message(error.message)}), error.status

    @app.errorhandler(IntegrityError)
    def conflict(error):
        db.session.rollback()
        return jsonify(error={"code": "conflict", "message": translate("数据已存在或已被修改，请刷新后重试。")}), 409

    @app.errorhandler(SQLAlchemyError)
    def database_error(error):
        db.session.rollback()
        # 不记录 SQL 参数，避免日记正文与密码进入日志。
        app.logger.error("数据库操作失败：%s", type(error).__name__)
        return jsonify(error={"code": "database_unavailable", "message": translate("暂时无法保存或读取数据，请稍后重试。")}), 503

    @app.errorhandler(HTTPException)
    def http_error(error):
        messages = {413: "文件过大，请缩小后重试。", 429: "尝试过于频繁，请稍后再试。", 404: "页面或资源不存在。", 405: "请求方法不支持。"}
        return jsonify(error={"code": str(error.code), "message": translate(messages.get(error.code, "请求无法完成。"))}), error.code

    return app
