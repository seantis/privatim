from datetime import timedelta, datetime
from sqlalchemy import select
from sedate import utcnow
from sqlalchemy.orm import selectinload

from privatim.models import User, WorkingGroup, Meeting
from privatim.utils import fix_utc_to_local_time


def get_pre_filled_content_on_searchable_field(page, field='attendees'):
    """
    Get a list of items that were pre-populated in the
    SearchableSelectMultipleField.

    It accesses the 'options' list from the specific nested structure
    in form_fields."""
    form_fields = page.form.fields
    attendees_options = form_fields[field][0].__dict__['options']
    return [entry[2] for entry in attendees_options if entry[1]]


def test_add_meeting_pre_populated(client):
    users = [
        User(email='max@example.org', first_name='Max', last_name='Müller'),
        User(
            email='alexa@example.org',
            first_name='Alexa',
            last_name='Troller',
        ),
        User(email='kurt@example.org', first_name='Kurt', last_name='Huber'),
    ]
    for user in users:
        user.set_password('test')
        client.db.add(user)
    client.db.commit()

    working_group = WorkingGroup(name='Test Group', leader=users[0])
    working_group.users.extend(users)
    client.db.add(working_group)
    client.db.commit()
    stmt = select(WorkingGroup.id).where(WorkingGroup.name == 'Test Group')
    group_id = client.db.execute(stmt).scalars().first()

    client.login_admin()
    page = client.get(f'/working_groups/{group_id}/add')

    # People from Working Group are in form for adding meeting
    pre_filled = get_pre_filled_content_on_searchable_field(page)
    assert ['Max Müller', 'Alexa Troller', 'Kurt Huber'] == pre_filled
    page.form['name'] = 'Weekly Meeting'
    page.form['time'] = datetime.now().strftime('%Y-%m-%dT%H:%M')
    page.form['attendees'].select_multiple(texts=['Kurt Huber', 'Max Müller'])
    page = page.form.submit().follow()
    assert 'Weekly Meeting' in page


def test_edit_meeting(client):
    users = [
        User(email='max@example.org', first_name='Max', last_name='Müller'),
        User(
            email='alexa@example.org',
            first_name='Alexa',
            last_name='Troller',
        ),
        User(email='kurt@example.org', first_name='Kurt', last_name='Huber'),
    ]
    for user in users:
        user.set_password('test')
        client.db.add(user)
    client.db.commit()

    working_group = WorkingGroup(name='Test Group', leader=users[0])
    working_group.users.extend(users)
    client.db.add(working_group)
    client.db.commit()

    meeting_time = fix_utc_to_local_time(utcnow())
    # Create a meeting with Max and Alexa
    src_meeting = Meeting(
        name='Initial Meeting',
        time=meeting_time,
        attendees=users[:2],
        working_group=working_group,
    )
    client.db.add(src_meeting)
    client.db.commit()
    client.db.refresh(src_meeting)

    client.login_admin()

    page = client.get(f'/meetings/{src_meeting.id}/edit')
    assert page.status_code == 200

    # form should be filled
    assert page.form.fields['name'][0].__dict__['_value'] == 'Initial Meeting'
    assert get_pre_filled_content_on_searchable_field(page) == [
        'Max Müller', 'Alexa Troller'
    ]

    # Test the cancel button, if cancel edit meeting redirected to the meeting
    page = page.click('Abbrechen')
    assert f'meeting/{src_meeting.id}' in page.request.url

    page = client.get(f'/meetings/{src_meeting.id}/edit')
    # Modify the meeting details
    new_meeting_time = meeting_time + timedelta(days=1)
    page.form['name'] = 'Updated Meeting'
    page.form['time'] = new_meeting_time.strftime('%Y-%m-%dT%H:%M')
    page.form['attendees'].select_multiple(texts=['Kurt Huber', 'Max Müller'])
    page = page.form.submit().follow()
    assert 'Dieses Feld wird benötigt' not in page

    assert 'Updated Meeting' in page
    assert 'Kurt Huber' in page
    assert 'Max Müller' in page

    # copy Agenda Items
    # need to first create another meeting to copy to
    meeting_time = fix_utc_to_local_time(utcnow())
    dest_meeting = Meeting(
        name='Destination Meeting',
        time=meeting_time,
        attendees=users[:2],
        working_group=working_group,
    )
    client.db.add(dest_meeting)
    client.db.commit()
    client.db.refresh(dest_meeting)

    page = client.get(f'/meetings/{src_meeting.id}/add')
    page.form['title'] = 'Agenda item'
    page.form['description'] = 'description'
    page.form.submit().follow()

    page = client.get(f'/meetings/{src_meeting.id}/copy_agenda_item')
    # Copy to dest_meeting, which is the only option, so this works
    page.form['copy_to'] = page.form['copy_to'].options[0][0]
    page.form['copy_description'] = True
    page.form.submit().follow()

    # Verify the agenda item was copied
    stmt = (
        select(Meeting)
        .options(
            selectinload(Meeting.agenda_items)
        )
        .where(Meeting.id == dest_meeting.id)
    )
    dest_updated = client.db.scalars(stmt).unique().one()
    assert dest_updated.agenda_items[0].title == 'Agenda item'
    assert dest_updated.agenda_items[0].description == 'description'

    # Check src isn't affected
    page = client.get(f'/meeting/{src_meeting.id}')
    agenda_items_div = page.pyquery('#agenda-items')[0]
    assert len(agenda_items_div) != 0
    text = agenda_items_div.text_content()
    assert 'Agenda item' in text
    assert 'description' in text

    # Delete the original meeting
    client.db.delete(src_meeting)
    client.db.flush()
    client.db.commit()

    # Verify the agenda item still exists in the destination meeting
    stmt = (
        select(Meeting)
        .options(
            selectinload(Meeting.agenda_items)
        )
        .where(Meeting.id == dest_meeting.id)
    )
    dest_updated = client.db.scalars(stmt).unique().one()
    assert dest_updated.agenda_items[0].title == 'Agenda item'
    assert dest_updated.agenda_items[0].description == 'description'


def test_copy_agenda_items_without_description(client):

    client.login_admin()
    users = [
        User(email='max@example.org', first_name='Max', last_name='Müller'),
        User(
            email='alexa@example.org',
            first_name='Alexa',
            last_name='Troller',
        ),
        User(email='kurt@example.org', first_name='Kurt', last_name='Huber'),
    ]
    for user in users:
        user.set_password('test')
        client.db.add(user)
    client.db.commit()

    working_group = WorkingGroup(name='Test Group', leader=users[0])
    working_group.users.extend(users)
    client.db.add(working_group)

    meeting_time = fix_utc_to_local_time(utcnow())
    src_meeting = Meeting(
        name='Initial Meeting',
        time=meeting_time,
        attendees=users[:2],
        working_group=working_group,
    )
    client.db.add(src_meeting)
    client.db.commit()
    client.db.refresh(src_meeting)

    # copy Agenda Items
    # need to first create another meeting to copy to
    dest_meeting = Meeting(
        name='Destination Meeting',
        time=meeting_time,
        attendees=users[:2],
        working_group=working_group,
    )
    client.db.add(dest_meeting)
    client.db.commit()
    client.db.refresh(dest_meeting)

    page = client.get(f'/meetings/{src_meeting.id}/add')
    page.form['title'] = 'Agenda item'
    page.form['description'] = 'description'
    page.form.submit().follow()

    page = client.get(f'/meetings/{src_meeting.id}/copy_agenda_item')
    page.form['copy_to'] = page.form['copy_to'].options[0][0]
    page.form['copy_description'] = False
    page.form.submit().follow()

    # Verify the agenda item was copied
    stmt = (
        select(Meeting)
        .options(
            selectinload(Meeting.agenda_items)
        )
        .where(Meeting.id == dest_meeting.id)
    )
    dest_updated = client.db.scalars(stmt).unique().one()
    assert dest_updated.agenda_items[0].title == 'Agenda item'
    # Description wasn't copied
    assert dest_updated.agenda_items[0].description == ''
