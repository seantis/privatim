from tests.shared.utils import Bunch
from sedate import utcnow
from sqlalchemy import select, func
from privatim.models import (
    AgendaItem,
    AgendaItemStatePreference,
    AgendaItemDisplayState,
    User,
    Meeting,
    WorkingGroup,
)
from privatim.views import update_single_agenda_item_state, \
    update_bulk_agenda_items_state


def test_update_agenda_item_state(pg_config):
    """Test setting and updating agenda item display state preferences"""

    # Add required routes
    pg_config.add_route('update_agenda_item_state', '/agenda-items/{id}/state')

    db = pg_config.dbsession

    # Create test user and agenda item
    user = User(email='test@example.com')
    agenda_item = AgendaItem(
        title='Test Item',
        description='Test Description',
        meeting=Meeting(
            name='Test Meeting',
            time=utcnow(),
            attendees=[user],
            working_group=WorkingGroup(name='Test Group'),
        ),
        position=1,
    )
    db.add_all([user, agenda_item])
    db.flush()

    # Create request with state change to EXPANDED
    request = Bunch(
        matchdict={'id': str(agenda_item.id)},
        json_body={'state': AgendaItemDisplayState.EXPANDED.value},
        user=user,
        dbsession=db,
    )
    request.user = user

    # Test creating new preference
    response = update_single_agenda_item_state(request)
    assert response == {'status': 'success'}

    # Verify preference was created
    preference = db.execute(
        select(AgendaItemStatePreference).where(
            AgendaItemStatePreference.agenda_item_id == agenda_item.id,
            AgendaItemStatePreference.user_id == user.id,
        )
    ).scalar_one()

    assert preference is not None
    assert preference.state == AgendaItemDisplayState.EXPANDED.value

    # Test updating existing preference to COLLAPSED
    request.json_body = {'state': AgendaItemDisplayState.COLLAPSED.value}
    response = update_single_agenda_item_state(request)
    assert response == {'status': 'success'}

    # Verify preference was updated
    preference = db.execute(
        select(AgendaItemStatePreference).where(
            AgendaItemStatePreference.agenda_item_id == agenda_item.id,
            AgendaItemStatePreference.user_id == user.id,
            )
    ).scalar_one()
    assert preference.state == AgendaItemDisplayState.COLLAPSED.value

    # Verify only one preference exists
    preference_count = db.scalar(
        select(func.count())
        .select_from(AgendaItemStatePreference)
        .where(
            AgendaItemStatePreference.agenda_item_id == agenda_item.id,
            AgendaItemStatePreference.user_id == user.id,
        )
    )
    assert preference_count == 1


def test_bulk_update_agenda_items_state(pg_config):
    """Test bulk updating display state preferences for multiple agenda
       items """
    # Add required routes
    pg_config.add_route(
        'bulk_update_agenda_items_state',
        '/meeting/{id}/agenda-items/bulk/state',
    )

    db = pg_config.dbsession

    # Create test user and meeting with multiple agenda items
    user = User(email='test@example.com')
    meeting = Meeting(
        name='Test Meeting',
        time=utcnow(),
        attendees=[user],
        working_group=WorkingGroup(name='Test Group'),
    )

    # Create three agenda items
    agenda_items = [
        AgendaItem(
            title=f'Test Item {i}',
            description=f'Test Description {i}',
            meeting=meeting,
            position=i,
        )
        for i in range(1, 4)
    ]

    db.add_all([user, meeting] + agenda_items)
    db.flush()

    # Create request with bulk state change to EXPANDED
    request = Bunch(
        matchdict={'id': str(meeting.id)},
        json_body={'state': AgendaItemDisplayState.EXPANDED.value},
        user=user,
        dbsession=db,
    )

    # Test creating new preferences for all items
    context = meeting
    response = update_bulk_agenda_items_state(context, request)
    assert response == {'status': 'success', 'updated': 3}

    # Verify preferences were created for all items
    for agenda_item in agenda_items:
        preference = db.execute(
            select(AgendaItemStatePreference).where(
                AgendaItemStatePreference.agenda_item_id == agenda_item.id,
                AgendaItemStatePreference.user_id == user.id,
            )
        ).scalar_one()
        assert preference is not None
        assert preference.state == AgendaItemDisplayState.EXPANDED.value

    # Test updating existing preferences to COLLAPSED
    request.json_body = {'state': AgendaItemDisplayState.COLLAPSED.value}
    response = update_bulk_agenda_items_state(meeting, request)
    assert response == {'status': 'success', 'updated': 3}

    # Verify all preferences were updated
    for agenda_item in agenda_items:
        preference = db.execute(
            select(AgendaItemStatePreference).where(
                AgendaItemStatePreference.agenda_item_id == agenda_item.id,
                AgendaItemStatePreference.user_id == user.id,
            )
        ).scalar_one()
        assert preference.state == AgendaItemDisplayState.COLLAPSED.value

    # Verify only one preference exists per agenda item
    for agenda_item in agenda_items:
        preference_count = db.scalar(
            select(func.count())
            .select_from(AgendaItemStatePreference)
            .where(
                AgendaItemStatePreference.agenda_item_id == agenda_item.id,
                AgendaItemStatePreference.user_id == user.id,
            )
        )
        assert preference_count == 1

    # Test mixed state scenario - delete one preference
    first_item_preference = db.execute(
        select(AgendaItemStatePreference).where(
            AgendaItemStatePreference.agenda_item_id == agenda_items[0].id,
            AgendaItemStatePreference.user_id == user.id,
        )
    ).scalar_one()
    db.delete(first_item_preference)
    db.flush()

    # Update states again
    request.json_body = {'state': AgendaItemDisplayState.EXPANDED.value}
    response = update_bulk_agenda_items_state(meeting, request)
    assert response['status'] == 'success'

    # Verify first item got new preference and others were updated
    new_preference = db.execute(
        select(AgendaItemStatePreference).where(
            AgendaItemStatePreference.agenda_item_id == agenda_items[0].id,
            AgendaItemStatePreference.user_id == user.id,
        )
    ).scalar_one()
    assert new_preference is not None
    assert new_preference.state == AgendaItemDisplayState.EXPANDED.value

    # Check total preference count is still correct
    total_preferences = db.scalar(
        select(func.count())
        .select_from(AgendaItemStatePreference)
        .where(
            AgendaItemStatePreference.user_id == user.id,
        )
    )
    assert total_preferences == len(agenda_items)
