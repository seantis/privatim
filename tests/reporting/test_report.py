from io import BytesIO
import pypdf
from babel.dates import format_datetime
from sedate import utcnow

from privatim.layouts.layout import DEFAULT_TIMEZONE
from privatim.models import AgendaItem
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


def test_html(pg_config):
    meeting = create_meeting()
    # add agenda items:
    items = [
        {
            'title': 'Item 1',
            'description': 'Description 1',
            'meeting': meeting,
            'position': 0,
        },
        {
            'title': 'Item 2',
            'description': 'Description 2',
            'meeting': meeting,
            'position': 1,
        },
    ]
    for item in items:
        meeting.agenda_items.append(AgendaItem(**item))

    renderer = HTMLReportRenderer()
    request = CustomDummyRequest()
    created_at = format_datetime(
        utcnow(),
        format='short',
        locale='de',
        tzinfo=DEFAULT_TIMEZONE,
    ).replace('\u202f', ' ')

    # todo: just use a string dateime.
    html = renderer.render_template(meeting, created_at, request)
    with open('/tmp/report.html', 'w') as f:
        f.write(html)
