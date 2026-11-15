"""管理员只能由具有服务器访问权的维护者显式创建，不提供公开提权接口。"""
import click
from sqlalchemy import select
from werkzeug.security import generate_password_hash

from .extensions import db
from .models import LocalSpace
from .models_workflow import Member, SpaceOwnership


def register_commands(app):
    @app.cli.command('reconcile-alipay')
    @click.option('--date', 'bill_date', required=True, type=click.DateTime(formats=['%Y-%m-%d']))
    @click.option('--bill', required=True, type=click.File('rb'))
    def reconcile_alipay(bill_date, bill):
        from .services.alipay import AlipayError
        from .services.alipay_reconciliation import compare_bill
        from .services.commerce import gateway
        client = gateway(required=False)
        if not client:
            raise click.ClickException('支付宝尚未配置。')
        try:
            missing, extra = compare_bill(bill.read(20 * 1024 * 1024 + 1), bill_date.date(), client)
        except (ValueError, AlipayError) as error:
            raise click.ClickException('账单格式或金额无效。') from error
        from json import dumps
        for label, rows in [('local_only', missing), ('bill_only', extra)]:
            for (merchant_no, provider_no, kind, batch, cents), count in rows.items():
                click.echo(dumps({'difference': label, 'merchantNo': merchant_no, 'providerNo': provider_no,
                                  'kind': kind, 'refundNo': batch, 'amountCents': cents, 'count': count},
                                 ensure_ascii=False))
        if missing or extra:
            raise click.ClickException('发现对账差异，须人工核对；本命令不会修改订单。')
        click.echo('本地交易与支付宝账单一致。')

    @app.cli.command('expire-alipay-orders')
    @click.option('--limit', default=25, type=click.IntRange(1, 100))
    def expire_alipay_orders(limit):
        from .services.commerce import expire_overdue, gateway
        if not gateway(required=False):
            raise click.ClickException('支付宝尚未配置。')
        checked, failed = expire_overdue(limit)
        click.echo(f'核对 {checked} 笔超时订单，{failed} 笔待渠道复核。')

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
