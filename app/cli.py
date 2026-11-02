"""管理员只能由具有服务器访问权的维护者显式创建，不提供公开提权接口。"""
import click
from sqlalchemy import select
from werkzeug.security import generate_password_hash

from .extensions import db
from .models import LocalSpace
from .models_workflow import Member, SpaceOwnership


def register_commands(app):
    @app.cli.command('create-admin')
    @click.option('--email', prompt='管理员邮箱')
    @click.option('--name', prompt='显示姓名')
    @click.password_option(confirmation_prompt=True)
    def create_admin(email, name, password):
        from .api.accounts import credentials
        from .security import APIError
        try:
            email, password = credentials({'email': email, 'password': password})
        except APIError as error:
            raise click.ClickException(error.message) from None
        if not name.strip() or len(name.strip()) > 80:
            raise click.ClickException('姓名须为 1—80 个字符。')
        if db.session.scalar(select(Member).where(Member.email == email)):
            raise click.ClickException('该邮箱已存在；不会自动提升已有用户权限。')
        member = Member(email=email, name=name.strip(), password_hash=generate_password_hash(password), role='admin')
        space = LocalSpace()
        db.session.add_all([member, space])
        db.session.flush()
        db.session.add(SpaceOwnership(space_id=space.id, member_id=member.id))
        db.session.commit()
        click.echo('管理员已建立。密码未写入配置或日志。')
