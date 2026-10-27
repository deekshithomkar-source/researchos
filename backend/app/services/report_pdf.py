"""PDF renderer with escaped text, embedded font and automatic pagination."""
from io import BytesIO
from pathlib import Path
from threading import Lock
from xml.sax.saxutils import escape
import reportlab
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from app.services.report_rendering import document_blocks

_font_lock = Lock()


class PdfReportRenderer:
    media_type = 'application/pdf'

    def render(self, report):
        with _font_lock:
            if 'ResearchOS' not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont('ResearchOS', str(Path(reportlab.__file__).parent / 'fonts' / 'Vera.ttf')))
        styles = getSampleStyleSheet()
        for style in styles.byName.values():
            style.fontName = 'ResearchOS'
        output = BytesIO()
        document = SimpleDocTemplate(output, title=report.title, author='ResearchOS')
        story = []
        for kind, text in document_blocks(report):
            style = styles[{'title': 'Title', 'heading': 'Heading1', 'subheading': 'Heading2', 'paragraph': 'BodyText'}[kind]]
            story.extend([Paragraph(escape(text), style), Spacer(1, 8)])
        def page_number(canvas, doc):
            canvas.saveState()
            canvas.setFont('ResearchOS', 9)
            canvas.drawRightString(550, 25, str(doc.page))
            canvas.restoreState()
        document.build(story, onFirstPage=page_number, onLaterPages=page_number)
        return output.getvalue()
