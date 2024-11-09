from io import BytesIO
import pypdf
from privatim.reporting.report import (MeetingReport, ReportOptions,
                                       HTMLReportRenderer)
from tests.shared.utils import create_meeting, CustomDummyRequest


def test_generate_meeting_report(pg_config):
    meeting = create_meeting()

    renderer = HTMLReportRenderer()
    request = CustomDummyRequest()
    report = MeetingReport(
        request, meeting, ReportOptions(language='de'), renderer
    )
    pdf = report.build()

    # with open('/tmp/report.pdf', 'wb') as f:
    #     f.write(pdf.data)

    document = pypdf.PdfReader(BytesIO(pdf.data))
    assert len(document.pages) > 0

    # read the pages
    extracted_text = ''.join(page.extract_text() for page in document.pages)
    assert 'John Doe' in extracted_text
    assert 'Schabala Babala' in extracted_text
    assert 'Waffle Workshop Group' in extracted_text
    assert 'Parade' in extracted_text
    assert 'Powerpoint' in extracted_text
