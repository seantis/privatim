from datetime import datetime, timezone
from sqlalchemy import select
from privatim.models import Meeting, User, AgendaItem, WorkingGroup


def test_working_group_meetings_relationship(session):

    date = datetime(
        2018,
        10,
        10,
        10,
        10,
        10,
        tzinfo=timezone.utc,
    )

    users = [
        User(email='foo@bar.ch'),
        User(email='schabala@babala.ch'),
    ]
    session.add_all(users)
    session.flush()
    group = WorkingGroup(name='Waffle Workshop Group', leader=users[0],
                         users=users)
    meeting = Meeting(name='Waffle Workshop', time=date, attendees=users,
                      working_group=group)
    session.add_all([meeting])
    session.flush()

    stored_meeting = session.execute(select(Meeting).filter_by(
        name='Waffle Workshop')
    ).scalar_one()
    assert stored_meeting is not None
    assert stored_meeting.time == date

    # Check that all users are associated with the meeting
    assert len(stored_meeting.attendees) == 2
    expected = {'foo@bar.ch', 'schabala@babala.ch'}
    assert {user.email for user in stored_meeting.attendees} == expected


def test_agenda_item_relationship_with_meeting(session):
    # Creating a meeting with a predefined date and attendees
    meeting_date = datetime(
        2023,
        5,
        1,
        12,
        0,
        0,
        tzinfo=timezone.utc,
    )
    attendees = [
        User(email='example@example.com'),
        User(email='another@example.com'),
    ]
    session.add_all(attendees)
    session.flush()

    group = WorkingGroup(name='Waffle Workshop Group', users=[])
    meeting = Meeting(
        name='Annual Review', time=meeting_date, attendees=attendees,
        working_group=group

    )
    session.add(meeting)
    session.flush()

    # Creating an agenda item linked to the meeting
    item = AgendaItem.create(
        session,
        title='Budget Overview',
        description='Detailed review of the year\'s budget and spending.',
        meeting=meeting
    )
    session.add(item)
    session.flush()

    # Retrieve and assert correct relationship mappings
    stored_agenda_item = (
        session.query(AgendaItem).filter_by(title='Budget Overview').one()
    )
    assert stored_agenda_item is not None
    assert stored_agenda_item.meeting_id == meeting.id

    # Assert meeting linkage and check if agenda items are correctly populated
    assert stored_agenda_item.meeting is not None
    assert stored_agenda_item.meeting.name == 'Annual Review'
    assert 'Budget Overview' in [
        item.title for item in stored_agenda_item.meeting.agenda_items
    ]
