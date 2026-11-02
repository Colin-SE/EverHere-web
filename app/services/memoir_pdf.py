"""从冻结材料生成固定版式成品及带预览标记的版本，不访问原始相册。"""
from io import BytesIO
from xml.sax.saxutils import escape

from PIL import Image as PILImage, ImageOps
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image


def render_pdf(snapshot, assets, layout, preview=False):
    if 'STSong-Light' not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
    stream = BytesIO()
    body = ParagraphStyle('Memory', fontName='STSong-Light', fontSize=layout.get('fontSize', 12), leading=20, wordWrap='CJK', spaceAfter=10)
    title = ParagraphStyle('MemoryTitle', parent=body, fontSize=24, leading=32, alignment=TA_CENTER, spaceAfter=24)
    heading = ParagraphStyle('MemoryHeading', parent=body, fontSize=18, leading=26, spaceAfter=18)
    story = [Spacer(1, 75), Paragraph(escape(snapshot['title']), title), Paragraph(escape(snapshot['theme']), body), PageBreak()]
    order = layout.get('chapterOrder', list(range(len(snapshot['chapters']))))
    for position, index in enumerate(order):
        chapter = snapshot['chapters'][index]
        story.append(Paragraph(escape(chapter['heading']), heading))
        if chapter.get('date'):
            story.append(Paragraph(escape(str(chapter['date'])), body))
        # 分段并对超长单段进一步切块，防止巨大 Paragraph 无法分页。
        for line in chapter['content'].splitlines():
            if not line:
                story.append(Spacer(1, 8))
            for start in range(0, len(line), 1500):
                story.append(Paragraph(escape(line[start:start + 1500]), body))
        for asset_id in chapter['photoAssetIds']:
            with PILImage.open(BytesIO(assets[asset_id].data)) as original:
                image = ImageOps.exif_transpose(original).convert('RGB')
                image.thumbnail((1600, 1600))
                output = BytesIO()
                image.save(output, format='JPEG', quality=90)
                width, height = image.size
            ratio = min(450 / width, 500 / height)
            story.extend([Spacer(1, 10), Image(BytesIO(output.getvalue()), width=width * ratio, height=height * ratio)])
        if position < len(order) - 1:
            story.append(PageBreak())

    def page_label(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 9)
        canvas.setFillColor(colors.HexColor('#6d6159'))
        canvas.drawRightString(550, 28, str(doc.page))
        if preview:
            canvas.drawString(45, 28, 'EVERHERE - PREVIEW / NOT A PURCHASED EDITION')
        canvas.restoreState()

    SimpleDocTemplate(stream, pagesize=(595.28, 841.89), rightMargin=50, leftMargin=50, topMargin=55, bottomMargin=55,
                      title=snapshot['title'], author='Everhere').build(story, onFirstPage=page_label, onLaterPages=page_label)
    return stream.getvalue()
