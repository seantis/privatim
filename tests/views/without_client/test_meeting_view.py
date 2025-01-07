
from privatim.testing import DummyRequest
from privatim.views import move_agenda_item
from tests.shared.utils import (
    create_meeting_with_agenda_items,
    verify_sequential_positions,
)


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from privatim.models import AgendaItem


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

    response = move_agenda_item(meeting, request)
    assert response['status'] == 'success'


def test_sortable_agenda_items_view_2(pg_config):
    # Add route
    pg_config.add_route(
        'sortable_agenda_items',
        '/meetings/agenda_items/{id}/move/{subject_id}/{direction}/{'
        'target_id}',
    )

    # Create a meeting with four agenda items
    db = pg_config.dbsession
    agenda_items = [
        {'title': 'Introduction', 'description': 'Welcome and introductions.'},
        {'title': 'Project Update', 'description': 'Update on projects.'},
        {'title': 'Budget Review', 'description': 'Financial overview.'},
        {'title': 'Next Steps', 'description': 'Action items and next steps.'}
    ]
    meeting = create_meeting_with_agenda_items(agenda_items, db)

    # Verify initial positions
    assert [[e.title, e.position] for e in meeting.agenda_items] == [
        ['Introduction', 0],
        ['Project Update', 1],
        ['Budget Review', 2],
        ['Next Steps', 3]
    ]
    print('Initial positions:', [[e.title, e.position] for e in meeting.agenda_items])
    verify_sequential_positions(meeting.agenda_items)

    # Test moving first item below second item
    request = DummyRequest()
    request.matchdict = {
        'id': str(meeting.id),
        'subject_id': '0',
        'direction': 'below',
        'target_id': '1',
    }
    request.method = 'POST'
    request.is_xhr = True

    response = move_agenda_item(meeting, request)
    assert response['status'] == 'success'

    print('Positions after moving Introduction below Project Update:',
          [[e.title, e.position] for e in meeting.agenda_items])
    verify_sequential_positions(meeting.agenda_items)

    assert [[e.title, e.position] for e in meeting.sorted_agenda_items] == [
        ['Project Update', 0],
        ['Introduction', 1],
        ['Budget Review', 2],
        ['Next Steps', 3]
    ]

    # Test moving last item above second-to-last item
    request.matchdict = {
        'id': str(meeting.id),
        'subject_id': '3',
        'direction': 'above',
        'target_id': '2',
    }

    response = move_agenda_item(meeting, request)
    assert response['status'] == 'success'
    verify_sequential_positions(meeting.agenda_items)
    assert [[e.title, e.position] for e in meeting.sorted_agenda_items] == [
        ['Project Update', 0],
        ['Introduction', 1],
        ['Next Steps', 2],
        ['Introduction', 3],
    ]

    # AssertionError: assert
# [['Project Update', 0],
# ['Budget Review', 1],
# ['Introduction', 2],
# ['Next Steps', 3]] ==

# [['Project Update', 0],
# ['Introduction', 1],
# ['Budget Review', 2],
# ['Next Steps', 3]]
