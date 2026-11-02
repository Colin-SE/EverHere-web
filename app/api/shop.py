"""F4 独立商城与订单确认；本阶段不提供付款或交付接口。"""
from hashlib import sha256
import json

from flask import Blueprint, g
from sqlalchemy import select

from ..extensions import db
from ..models import Photo
from ..models_workflow import Member, Product, ProductVariant, ShopOrder, ShopOrderItem, Memoir, MemoirRevision
from ..security import APIError, body, member_required, admin_required
from ..services.records import text

bp = Blueprint('shop', __name__, url_prefix='/api/v1')
KINDS = {'medal', 'gift', 'memoir_digital', 'memoir_paper'}


def variant_data(variant):
    return {'id': variant.id, 'name': variant.name, 'kind': variant.kind, 'priceCents': variant.price_cents, 'active': variant.active,
            'textRequired': variant.text_required, 'photoRequired': variant.photo_required, 'version': variant.version}


def product_data(product, staff=False):
    query = select(ProductVariant).where(ProductVariant.product_id == product.id).order_by(ProductVariant.id)
    if not staff:
        query = query.where(ProductVariant.active.is_(True))
    return {'id': product.id, 'name': product.name, 'description': product.description, 'active': product.active, 'version': product.version,
            'variants': [variant_data(v) for v in db.session.scalars(query)]}


@bp.get('/shop/products')
def catalogue():
    products = db.session.scalars(select(Product).where(Product.active.is_(True)).order_by(Product.name))
    return {'data': {'products': [product_data(p) for p in products]}}


@bp.get('/admin/products')
@admin_required
def admin_catalogue():
    return {'data': {'products': [product_data(p, True) for p in db.session.scalars(select(Product).order_by(Product.name))]}}


def boolean(data, name, default):
    value = data.get(name, default)
    if type(value) is not bool:
        raise APIError('商品开关须为布尔值。', code=name)
    return value


def save_product(data, product=None):
    name = text(data.get('name'), '商品名称', 120)
    if not name:
        raise APIError('请填写商品名称。', code='name')
    variants = data.get('variants')
    if not isinstance(variants, list) or not 1 <= len(variants) <= 20:
        raise APIError('请提供 1—20 个商品款式。', code='variants')
    product = product or Product()
    product.name = name
    product.description = text(data.get('description'), '商品说明', 2000)
    product.active = boolean(data, 'active', False)
    db.session.add(product)
    db.session.flush()
    existing = {v.id: v for v in db.session.scalars(select(ProductVariant).where(ProductVariant.product_id == product.id).with_for_update())}
    seen = set()
    for raw in variants:
        if not isinstance(raw, dict):
            raise APIError('商品款式无效。', code='variants')
        variant_id = raw.get('id')
        if variant_id and (variant_id not in existing or variant_id in seen):
            raise APIError('款式不存在或重复。', code='variants')
        seen.add(variant_id)
        kind, price = raw.get('kind'), raw.get('priceCents')
        if not isinstance(kind, str) or kind not in KINDS:
            raise APIError('商品类型无效。', code='kind')
        if type(price) is not int or not 1 <= price <= 10_000_000:
            raise APIError('价格须为 1—10000000 分的整数。', code='priceCents')
        variant = existing.get(variant_id) or ProductVariant(product_id=product.id)
        variant.name = text(raw.get('name'), '款式名称', 120)
        if not variant.name:
            raise APIError('请填写款式名称。', code='name')
        variant.kind, variant.price_cents = kind, price
        variant.active = boolean(raw, 'active', True)
        variant.text_required = boolean(raw, 'textRequired', kind in {'gift', 'medal'})
        variant.photo_required = boolean(raw, 'photoRequired', False)
        if variant_id:
            variant.version += 1
        db.session.add(variant)
    # 省略的款式下架而非删除，保留历史订单引用。
    for variant_id in existing.keys() - seen:
        existing[variant_id].active = False
        existing[variant_id].version += 1
    return product


@bp.post('/admin/products')
@admin_required
def create_product():
    product = save_product(body())
    db.session.commit()
    return {'data': product_data(product, True)}, 201


@bp.put('/admin/products/<product_id>')
@admin_required
def update_product(product_id):
    data = body()
    product = db.session.scalar(select(Product).where(Product.id == product_id).with_for_update().execution_options(populate_existing=True))
    if not product:
        raise APIError('商品不存在。', 404)
    if type(data.get('version')) is not int or data['version'] != product.version:
        raise APIError('商品已更新，请刷新后编辑。', 409, 'version_conflict')
    save_product(data, product)
    product.version += 1
    db.session.commit()
    return {'data': product_data(product, True)}


def order_data(order):
    items = db.session.scalars(select(ShopOrderItem).where(ShopOrderItem.order_id == order.id))
    return {'id': order.id, 'state': order.state, 'totalCents': order.total_cents, 'createdAt': order.created_at.isoformat() + 'Z',
            'paymentAvailable': False, 'items': [{'id': i.id, 'quantity': i.quantity, 'unitPriceCents': i.unit_price_cents, 'snapshot': i.snapshot} for i in items]}


@bp.get('/shop/orders')
@member_required
def orders():
    items = db.session.scalars(select(ShopOrder).where(ShopOrder.buyer_id == g.member.id).order_by(ShopOrder.created_at.desc()))
    return {'data': {'orders': [order_data(o) for o in items]}}


@bp.get('/shop/orders/<order_id>')
@member_required
def order_detail(order_id):
    order = db.session.get(ShopOrder, order_id)
    if not order or order.buyer_id != g.member.id:
        raise APIError('订单不存在。', 404)
    return {'data': order_data(order)}


@bp.post('/shop/orders')
@member_required
def create_order():
    data = body()
    key = text(data.get('requestKey'), '请求编号', 64)
    if len(key) < 16:
        raise APIError('请提供有效请求编号。', code='requestKey')
    rows = data.get('items')
    if not isinstance(rows, list) or not 1 <= len(rows) <= 10 or any(not isinstance(row, dict) for row in rows):
        raise APIError('订单须包含 1—10 项商品。', code='items')
    digest = sha256(json.dumps(rows, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    # 账户级锁保证网络重试只创建一份订单，数据库唯一约束进一步兜底。
    db.session.execute(select(Member).where(Member.id == g.member.id).with_for_update()).scalar_one()
    previous = db.session.scalar(select(ShopOrder).where(ShopOrder.buyer_id == g.member.id, ShopOrder.request_key == key))
    if previous:
        if previous.request_hash != digest:
            raise APIError('请求编号已用于其他内容，请重新确认。', 409, 'idempotency_conflict')
        return {'data': {**order_data(previous), 'replayed': True}}
    if any(not isinstance(row.get('variantId'), str) for row in rows):
        raise APIError('请选择有效款式。', code='variantId')
    # 所有商品按同一顺序加锁，价格/上下架与下单不能交错。
    product_ids = list(db.session.scalars(select(ProductVariant.product_id).where(ProductVariant.id.in_([r['variantId'] for r in rows]))))
    products = {p.id: p for p in db.session.scalars(select(Product).where(Product.id.in_(product_ids)).order_by(Product.id).with_for_update().execution_options(populate_existing=True))}
    variants = {v.id: v for v in db.session.scalars(select(ProductVariant).where(ProductVariant.id.in_([r['variantId'] for r in rows])).order_by(ProductVariant.id).with_for_update().execution_options(populate_existing=True))}
    order = ShopOrder(buyer_id=g.member.id, request_key=key, request_hash=digest, total_cents=0)
    db.session.add(order)
    db.session.flush()
    for row in rows:
        variant = variants.get(row['variantId'])
        product = products.get(variant.product_id) if variant else None
        if not variant or not variant.active or not product or not product.active:
            raise APIError('商品或款式已下架，请重新选择。', 409, 'variantId')
        if type(row.get('variantVersion')) is not int or row['variantVersion'] != variant.version or type(row.get('productVersion')) is not int or row['productVersion'] != product.version:
            raise APIError('商品信息或价格已变化，请刷新后重新确认。', 409, 'price_changed')
        quantity = row.get('quantity', 1)
        if type(quantity) is not int or not 1 <= quantity <= 10:
            raise APIError('每项数量须为 1—10。', code='quantity')
        custom_text = text(row.get('customText'), '定制文字', 300)
        if variant.text_required and not custom_text:
            raise APIError('请填写此款式所需的定制文字。', code='customText')
        photo_uri, photo = row.get('photoUri'), None
        if photo_uri:
            if not isinstance(photo_uri, str) or not photo_uri.startswith('/api/v1/photos/'):
                raise APIError('请选择本人上传的照片。', code='photoUri')
            photo = db.session.get(Photo, photo_uri.rsplit('/', 1)[-1])
            if not photo or photo.user_id != g.owner.id:
                raise APIError('所选照片不存在或不属于本人。', code='photoUri')
            if row.get('authorisePhoto') is not True:
                raise APIError('请确认将照片用于本订单。', code='authorisePhoto')
            if len(photo.data) > 10 * 1024 * 1024:
                raise APIError('定制照片最多 10 MiB，请另选照片。', 413, 'photoUri')
        if variant.photo_required and not photo:
            raise APIError('此款式必须选择定制照片。', code='photoUri')
        revision_id = row.get('revisionId')
        if revision_id is not None and (not isinstance(revision_id, str) or not revision_id):
            raise APIError('回忆录版本无效。', code='revisionId')
        if variant.kind.startswith('memoir_'):
            revision = db.session.get(MemoirRevision, revision_id) if isinstance(revision_id, str) else None
            memoir = db.session.get(Memoir, revision.memoir_id) if revision else None
            if not revision or not memoir or memoir.owner_id != g.member.id or memoir.state != 'ready' or revision.state != 'ready' or revision.number != memoir.revision_number:
                raise APIError('请选择本人已制作完成的回忆录版本。', code='revisionId')
        elif revision_id:
            raise APIError('普通纪念品不需要绑定回忆录。', code='revisionId')
        snapshot = {'productName': product.name, 'variantName': variant.name, 'kind': variant.kind, 'customText': custom_text,
                    'photoAuthorised': photo is not None, 'photoChecksum': sha256(photo.data).hexdigest() if photo else None,
                    'revisionId': revision_id, 'currency': 'CNY'}
        item = ShopOrderItem(order_id=order.id, variant_id=variant.id, revision_id=revision_id, quantity=quantity, unit_price_cents=variant.price_cents,
                             snapshot=snapshot, photo_data=photo.data if photo else None, photo_type=photo.content_type if photo else None)
        db.session.add(item)
        order.total_cents += quantity * variant.price_cents
    db.session.commit()
    return {'data': order_data(order)}, 201
