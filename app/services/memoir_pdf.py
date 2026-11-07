"""从冻结材料制作成品；样张仅复制部分页面，绝不附带完整 PDF。"""
from io import BytesIO
from xml.sax.saxutils import escape

from PIL import Image as PILImage, ImageOps
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image


def render_pdf(snapshot, assets, layout, preview=False):
    if preview:
        return sample_pdf(render_pdf(snapshot, assets, layout))
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
        canvas.restoreState()

    SimpleDocTemplate(stream, pagesize=(595.28, 841.89), rightMargin=50, leftMargin=50, topMargin=55, bottomMargin=55,
                      title=snapshot['title'], author='Everhere').build(story, onFirstPage=page_label, onLaterPages=page_label)
    return stream.getvalue()


def sample_pdf(final):
    """最多两页，且至少保留一页不公开；两页短稿只展示封面。"""
    reader = PdfReader(BytesIO(final))
    if len(reader.pages) < 2:
        raise ValueError('成品至少需要封面和一页正文。')
    writer = PdfWriter()
    for page in list(reader.pages)[:min(2, len(reader.pages) - 1)]:
        sample_page = writer.add_page(page, excluded_keys=['/Annots', '/B'])
        overlay = BytesIO()
        label = pdfcanvas.Canvas(overlay, pagesize=(float(page.mediabox.width), float(page.mediabox.height)))
        label.setFont('Helvetica', 8)
        label.drawString(45, 40, 'EVERHERE - SAMPLE PAGES ONLY / NOT A PURCHASED EDITION')
        label.save()
        sample_page.merge_page(PdfReader(overlay).pages[0])
        # 不从原 PDF 复制书签、附件或其余页面引用。
    writer.add_metadata({'/Title': 'Everhere sample preview', '/Author': 'Everhere'})
    output = BytesIO()
    writer.write(output)
    return output.getvalue()
