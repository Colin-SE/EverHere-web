"""商品封面：公开与管理员边界、实际图片校验及版本保护。"""
from io import BytesIO
import pytest
from PIL import Image
from app.extensions import db
from app.models_workflow import Product
from conftest import Client
from test_workflows import administrator, register, product, image_bytes


def upload_cover(client, item, raw=None):
    return client.client.post('/api/v1/admin/products/'+item['id']+'/image',
        data={'version':str(item['version']), 'image':(BytesIO(raw if raw is not None else image_bytes()),'cover.png')},
        headers={'X-CSRF-Token':client.token})


def test_product_cover_permissions_publication_and_version(app,client):
    register(client)
    admin=administrator(app)
    item=product(admin)
    assert item['imageUrl'] is None
    assert upload_cover(client,item).status_code==403
    uploaded=upload_cover(admin,item)
    assert uploaded.status_code==200,uploaded.json
    saved=uploaded.json['data']
    assert saved['imageUrl'] and saved['version']==item['version']+1
    public=Client(app)
    response=public.client.get(saved['imageUrl'])
    assert response.status_code==200 and response.mimetype=='image/webp'
    with Image.open(BytesIO(response.data)) as image:
        assert image.format=='WEBP'
    assert upload_cover(admin,item).status_code==409
    item={**saved,'active':False}
    hidden=admin.call('PUT','/admin/products/'+item['id'],item).json['data']
    assert public.client.get(hidden['imageUrl']).status_code==404
    assert admin.client.get(hidden['imageUrl']).status_code==200
    assert client.call('DELETE','/admin/products/'+item['id']+'/image',{'version':hidden['version']}).status_code==403
    cleared=admin.call('DELETE','/admin/products/'+item['id']+'/image',{'version':hidden['version']})
    assert cleared.status_code==200 and cleared.json['data']['imageUrl'] is None
    assert admin.client.get(hidden['imageUrl']).status_code==404


@pytest.mark.parametrize('raw,status',[(b'<svg></svg>',400),(b'broken image',400),(b'x'*(5*1024*1024+1),413)],ids=['svg','broken','oversized'])
def test_invalid_cover_does_not_replace_existing_image(app,raw,status):
    admin=administrator(app)
    item=product(admin)
    saved=upload_cover(admin,item).json['data']
    before=admin.client.get(saved['imageUrl']).data
    result=upload_cover(admin,saved,raw)
    assert result.status_code==status
    assert result.json['error']['code']=='product_image'
    assert admin.client.get(saved['imageUrl']).data==before
    with app.app_context():
        assert db.session.get(Product,item['id']).version==saved['version']
