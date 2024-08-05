from privatim.testing import DummyRequest
from privatim.views import sortable_agenda_items_view
from tests.shared.utils import create_meeting_with_agenda_items


def test_sortable_agenda_items_view(pg_config):

    # Add route
    pg_config.add_route(
        'sortable_agenda_items',
        '/meetings/agenda_items/{id}/move/{subject_id}/{direction}/{'
        'target_id}',
    )

    # Create a meeting with agenda items
    db = pg_config.dbsession

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
