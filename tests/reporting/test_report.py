from io import BytesIO
import pypdf
from privatim.reporting.report import (MeetingReport, ReportOptions,
                                       HTMLReportRenderer)
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
from shared.utils import create_meeting, CustomDummyRequest


def test_simple_report():
    font_config = FontConfiguration()
    html = HTML(string='<h1>The title</h1>')
    css = CSS(string='''
        @font-face {
            font-family: Gentium;
            src: url(https://example.com/fonts/Gentium.otf);
        }
        h1 { font-family: Gentium }''', font_config=font_config)
    html.write_pdf('example.pdf', stylesheets=[css], font_config=font_config)


def test_generate_meeting_report(config):
    meeting = create_meeting()

    renderer = HTMLReportRenderer()
    request = CustomDummyRequest()

    report = MeetingReport(
        request, meeting, ReportOptions(language='de'), renderer
    )
    pdf = report.build()
    document = pypdf.PdfReader(BytesIO(pdf.data))

    assert len(document.pages) > 0

    # read the pages
    all_text = ''.join(page.extract_text() for page in document.pages)
    assert 'John Doe' in all_text
    assert 'Schabala Babala' in all_text
    assert 'Waffle Workshop Group' in all_text
    assert 'Parade' in all_text
    assert 'Powerpoint' in all_text
    assert 'Logo' in all_text
