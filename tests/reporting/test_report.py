import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO
import pypdf
from pyramid.events import BeforeRender
from privatim import add_renderer_globals
from privatim.reporting.report import (MeetingReport, ReportOptions,
                                       HTMLReportRenderer)
from tests.shared.utils import (
    create_meeting,
    create_meeting_with_agenda_items,
    CustomDummyRequest,
)


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


def test_meeting_report_does_not_fetch_files_or_urls(pg_config, tmp_path):
    """ HTML in agenda items must neither fetch local files (embedded as
    PDF attachments) nor reach internal hosts (SSRF). """

    secret = tmp_path / 'secret.ini'
    secret.write_text('session.secret = SECRET_MARKER\n')

    hits = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            hits.append(self.path)
            self.send_response(404)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = HTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]

    title = f'<link rel="attachment" href="file://{secret}">'
    description = (
        f'<a rel="attachment" href="file://{secret}">x</a>'
        f'<img src="http://127.0.0.1:{port}/internal">'
    )
    pg_config.add_subscriber(add_renderer_globals, BeforeRender)
    try:
        meeting = create_meeting_with_agenda_items(
            [{'title': title, 'description': description}],
            pg_config.dbsession,
        )
        report = MeetingReport(
            CustomDummyRequest(),
            meeting,
            ReportOptions(language='de'),
            HTMLReportRenderer(),
        )
        pdf = report.build().data
    finally:
        server.shutdown()

    assert b'/EmbeddedFile' not in pdf
    assert b'SECRET_MARKER' not in pdf
    assert hits == []

    document = pypdf.PdfReader(BytesIO(pdf))
    extracted_text = ''.join(page.extract_text() for page in document.pages)
    assert '<link rel="attachment"' in extracted_text
