import io
import pypdf
from privatim.testing import DummyRequest
from privatim.views import export_meeting_as_pdf_view, \
    sortable_agenda_items_view

from tests.shared.utils import create_meeting, CustomDummyRequest, \
    create_meeting_with_agenda_items


def test_export_meeting_without_agenda_items(pg_config):
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


def test_sortable_agenda_items_view(pg_config):

    # Add route
    config.add_route(
        'sortable_agenda_items',
        '/meetings/agenda_items/{id}/move/{subject_id}/{direction}/{'
        'target_id}',
    )

    # Create a meeting with agenda items
    db = config.dbsession

    agenda_items = [
        {'title': 'Introduction', 'description': 'Welcome and introductions.'},
        {'title': 'Project Update', 'description': 'Update on projects.'},
    ]
    meeting = create_meeting_with_agenda_items(agenda_items, db)
    assert [[e.title, e.position] for e in meeting.agenda_items] == [
        ['Introduction', 0],
        ['Project Update', 1]
    ]

    # assert zero based indexing
    all_pos = {e.position for e in meeting.agenda_items}
    assert all_pos == {0, 1}

    # print([item.title for item in meeting.agenda_items])
    request = DummyRequest()
    #  0 below 1 == swap the items
    request.matchdict = {
        'id': str(meeting.id),
        'subject_id': '0',
        'direction': 'below',
        'target_id': '1',
    }
    request.method = "POST"
    request.is_xhr = True

    response = sortable_agenda_items_view(meeting, request)
    assert response['status'] == 'success'
