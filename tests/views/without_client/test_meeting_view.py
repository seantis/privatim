import io
import pypdf
from privatim.views import export_meeting_as_pdf_view

from tests.shared.utils import create_meeting, CustomDummyRequest


def test_export_meeting_without_agenda_items(config):
    config.add_route('export_meeting_as_pdf_view',
                     '/meetings/{id}/export')

    db = config.dbsession
    meeting = create_meeting()

    db.add(meeting)
    db.flush()

    request = CustomDummyRequest()
    response = export_meeting_as_pdf_view(meeting, request)

    document = pypdf.PdfReader(io.BytesIO(response.body))
    all_text = ''.join(page.extract_text() for page in document.pages)
    assert 'John Doe' in all_text
    assert 'Schabala Babala' in all_text
    assert 'Waffle Workshop Group' in all_text
    assert 'Parade' in all_text
    assert 'Powerpoint' in all_text
    assert 'Logo' in all_text
