"""核对支付宝下载的业务明细表，仅报告差异。"""
import csv
import io
from collections import Counter
from datetime import datetime, time, timedelta, timezone

from sqlalchemy import select

from ..extensions import db
from ..models_trade import OrderTrade, TradeEvent
from .alipay import SHANGHAI, AlipayError, amount_cents

TRADE_NO = '支付宝交易号'
MERCHANT_NO = '商户订单号'
BUSINESS = '业务类型'
AMOUNT = '订单金额（元）'
REFUND_BATCH = '退款批次号'


def parse_bill(raw):
    if len(raw) > 20 * 1024 * 1024:
        raise ValueError('账单文件超过 20 MiB。')
    try:
        decoded = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        decoded = raw.decode('gb18030')
    lines = (line for line in io.StringIO(decoded) if line.strip() and not line.lstrip().startswith('#'))
    rows = csv.DictReader(lines)
    if not {TRADE_NO, MERCHANT_NO, BUSINESS, AMOUNT, REFUND_BATCH}.issubset({field.strip() for field in rows.fieldnames or []}):
        raise ValueError('请提供支付宝业务账单的中文交易明细 CSV。')
    actual = Counter()
    for abbreviated in rows:
        row = {key.strip(): (val or '').strip() for key, val in abbreviated.items() if key is not None}
        if row[BUSINESS] not in ('交易', '退款'):
            raise ValueError('账单包含未支持的业务类型。')
        fee = row[AMOUNT].lstrip('-') if row[BUSINESS] == '退款' else row[AMOUNT]
        actual[(row[MERCHANT_NO], row[TRADE_NO], row[BUSINESS],
                row[REFUND_BATCH] if row[BUSINESS] == '退款' else '', amount_cents(fee))] += 1
    return actual


def compare_bill(raw, date, client):
    actual = parse_bill(raw)
    start = datetime.combine(date, time(), SHANGHAI).astimezone(timezone.utc).replace(tzinfo=None)
    end = start + timedelta(days=1)
    query = select(OrderTrade, TradeEvent.kind).join(TradeEvent, OrderTrade.order_id == TradeEvent.order_id)
    query = query.where(TradeEvent.kind.in_(['paid', 'late_payment', 'refunded']),
                        TradeEvent.created_at >= start, TradeEvent.created_at < end,
                        OrderTrade.app_id == client.app_id, OrderTrade.seller_id == client.seller_id,
                        OrderTrade.environment == client.environment)
    expected = Counter((trade.merchant_no, trade.provider_no, '退款' if kind == 'refunded' else '交易',
                        trade.refund_no if kind == 'refunded' else '', trade.amount_cents)
                       for trade, kind in db.session.execute(query))
    return expected - actual, actual - expected
