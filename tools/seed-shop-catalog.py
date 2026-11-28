"""同步公开商品与配图；默认预览，不修改既有订单、库存或支付配置。"""
import argparse
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
from uuid import NAMESPACE_URL, uuid5


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app-root', type=Path, required=True)
    parser.add_argument('--site', choices=('production', 'sandbox'), required=True)
    parser.add_argument('--expected-database', required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--asset-dir', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    root = args.app_root.resolve(strict=True)
    sys.path.insert(0, str(root))

    from sqlalchemy import select
    from sqlalchemy.engine import make_url
    from app import create_app
    from app.extensions import db
    from app.models_workflow import Product, ProductVariant
    from app.services.product_images import prepare_cover

    if args.site == 'production':
        application = create_app()
        expected = 'life_album'
    else:
        spec = importlib.util.spec_from_file_location('catalog_sandbox', root / 'tools/alipay-sandbox-server.py')
        setup = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(setup)
        application = create_app({'SQLALCHEMY_DATABASE_URI': setup.database_url(), 'ALIPAY_MODE': 'disabled'})
        expected = 'life_album_alipay_sandbox'
    url = make_url(application.config['SQLALCHEMY_DATABASE_URI'])
    if url.get_backend_name() != 'mysql' or url.database != expected or args.expected_database != expected:
        raise RuntimeError('目标站点与明确指定的 MySQL 库名不匹配。')

    manifest = json.loads(args.manifest.read_text(encoding='utf-8-sig'))
    assets = args.asset_dir.resolve(strict=True)

    def cover(filename):
        path = (assets / filename).resolve(strict=True)
        if path.parent != assets:
            raise RuntimeError('图片必须位于明确指定的素材目录。')
        return prepare_cover(path.read_bytes())

    def stable_id(key):
        return str(uuid5(NAMESPACE_URL, 'https://wyever.com/catalog/' + key))

    protected_tables = ('shop_orders', 'shop_order_items', 'shop_order_trades', 'shop_trade_events', 'shop_order_events')

    def order_fingerprint():
        result = {}
        for name in protected_tables:
            table = db.metadata.tables[name]
            rows = [dict(row) for row in db.session.execute(select(table).order_by(table.c.id if 'id' in table.c else table.c.order_id)).mappings()]
            encoded = json.dumps(rows, sort_keys=True, ensure_ascii=False, default=str).encode('utf-8')
            result[name] = {'count': len(rows), 'sha256': sha256(encoded).hexdigest()}
        return result

    with application.app_context():
        before = order_fingerprint()
        operations = []
        plan = []
        keys = set()
        for item in manifest['products']:
            key, variant = item['key'], item['variant']
            if key in keys or not item['name'] or len(item['name']) > 120 or len(item['description']) > 2000:
                raise RuntimeError('商品清单存在重复或无效字段。')
            keys.add(key)
            if variant['kind'] not in ('gift', 'medal', 'memoir_digital', 'memoir_paper'):
                raise RuntimeError('不支持的商品交付类型。')
            if type(variant['priceCents']) is not int or not 1 <= variant['priceCents'] <= 10_000_000:
                raise RuntimeError('无效商品价格。')
            for field in ('textRequired', 'photoRequired'):
                if type(variant[field]) is not bool:
                    raise RuntimeError('无效定制开关。')
            product_id = stable_id(key)
            product = db.session.get(Product, product_id)
            if product is None:
                product = db.session.scalar(select(Product).where(Product.name == item['name']))
            if product and product.id == product_id and product.name != item['name']:
                raise RuntimeError('稳定商品编号已被其他商品使用。')
            data, mime = cover(item['image'])
            desired = dict(name=item['name'], description=item['description'], active=True,
                           image_type=mime, image_data=data)
            changed = [name for name, value in desired.items() if product is None or getattr(product, name) != value]
            variant_id = stable_id(key + '/standard')
            existing_variant = db.session.get(ProductVariant, variant_id)
            if existing_variant and (product is None or existing_variant.product_id != product.id):
                raise RuntimeError('稳定规格编号属于其他商品。')
            if existing_variant is None and product:
                existing_variant = db.session.scalar(select(ProductVariant).where(
                    ProductVariant.product_id == product.id, ProductVariant.name == variant['name']))
            variant_values = dict(name=variant['name'], kind=variant['kind'], price_cents=variant['priceCents'],
                                  active=True, text_required=variant['textRequired'], photo_required=variant['photoRequired'])
            variant_changed = [name for name, value in variant_values.items()
                               if existing_variant is None or getattr(existing_variant, name) != value]
            operations.append((product, product_id, desired, changed, existing_variant, variant_id,
                               variant_values, variant_changed))
            plan.append(dict(name=item['name'], productId=product.id if product else product_id,
                             action='create' if product is None else 'update' if changed or variant_changed else 'unchanged',
                             productFields=changed, variantFields=variant_changed,
                             priceCents=variant['priceCents'], imageSha256=sha256(data).hexdigest()))

        legacy = []
        for item in manifest.get('coverOnly', []):
            product = db.session.scalar(select(Product).where(Product.name == item['name']))
            if product:
                data, mime = cover(item['image'])
                changed = product.image_data != data or product.image_type != mime
                legacy.append((product, data, mime, changed))
                plan.append(dict(name=product.name, productId=product.id, action='cover-only' if changed else 'unchanged'))

        if args.apply:
            for product, product_id, desired, changed, variant, variant_id, values, variant_changed in operations:
                product_existed = product is not None
                if product is None:
                    product = Product(id=product_id, **desired)
                    db.session.add(product)
                    db.session.flush()
                elif changed:
                    for name, value in desired.items():
                        setattr(product, name, value)
                    product.version += 1
                if variant is None:
                    db.session.add(ProductVariant(id=variant_id, product_id=product.id,
                                                  stock_available=None, **values))
                    if product_existed and not changed:
                        product.version += 1
                elif variant_changed:
                    for name, value in values.items():
                        setattr(variant, name, value)
                    variant.version += 1
                    if product is not None and not changed:
                        product.version += 1
            for product, data, mime, changed in legacy:
                if changed:
                    product.image_data, product.image_type = data, mime
                    product.version += 1
            db.session.flush()
            if before != order_fingerprint():
                db.session.rollback()
                raise RuntimeError('既有订单指纹发生变化，已回滚。')
            db.session.commit()
        else:
            db.session.rollback()

        print(json.dumps({'site': args.site, 'database': expected, 'applied': args.apply, 'products': plan,
                          'existingOrderTablesUnchanged': True,
                          'existingOrderCounts': {name: value['count'] for name, value in before.items()}}, ensure_ascii=False))


if __name__ == '__main__':
    main()
