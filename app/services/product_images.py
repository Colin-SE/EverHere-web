"""商品公开封面校验与统一编码；不改动私人相册原图。"""
from io import BytesIO
import warnings
from PIL import Image, ImageOps, UnidentifiedImageError
from ..security import APIError

MAX_COVER_BYTES = 5 * 1024 * 1024


def prepare_cover(raw):
    if not raw or len(raw) > MAX_COVER_BYTES:
        raise APIError('商品图片不能超过 5 MiB。', 413, 'product_image')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(BytesIO(raw)) as original:
                if original.format not in {'JPEG', 'PNG', 'WEBP'} or original.width * original.height > 16_000_000:
                    raise APIError('请选择不超过 1600 万像素的 JPEG、PNG 或 WebP 商品图片。', code='product_image')
                original.verify()
            with Image.open(BytesIO(raw)) as original:
                image = ImageOps.exif_transpose(original)
                image.thumbnail((1280, 1280))
                # 透明上传图铺暖白底，去除文件元信息后统一保存公开展示副本。
                layer = image.convert('RGBA')
                background = Image.new('RGBA', layer.size, '#fffefa')
                background.alpha_composite(layer)
                output = BytesIO()
                background.convert('RGB').save(output, format='WEBP', quality=88)
        return output.getvalue(), 'image/webp'
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise APIError('商品图片无法读取，请选择有效图片。', code='product_image') from None
