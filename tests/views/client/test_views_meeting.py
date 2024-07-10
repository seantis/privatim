from datetime import timedelta
from sedate import utcnow
from privatim.models import User, WorkingGroup, Meeting
from privatim.utils import fix_utc_to_local_time


def test_view_edit_meeting(client):
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
    # Create a meeting iwth Max and Alexa
    meeting = Meeting(
        name='Initial Meeting',
        time=meeting_time,
        attendees=users[:2],
        working_group=working_group,
    )
    client.db.add(meeting)
    client.db.commit()
    client.db.refresh(meeting)

    client.login_admin()

    page = client.get(f'/meetings/{meeting.id}/edit')
    assert page.status_code == 200

    def get_attendees(page, field='attendees'):
        """
        Get a list of items that were pre-populated.

        It accesses the 'options' list from the specific nested structure
        in form_fields."""
        form_fields = page.form.fields
        attendees_options = form_fields[field][0].__dict__['options']
        return [entry[2] for entry in attendees_options if entry[1]]

    # form should be populated:
    assert page.form.fields['name'][0].__dict__['_value'] == 'Initial Meeting'
    # assert get_attendees(page) == ['Max Müller', 'Alexa Troller']

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

    page = client.get(f'/meetings/{meeting.id}/add')
    page.form['title'] = 'my title'
    page.form['description'] = 'description'
    page = page.form.submit().follow()

    page = client.get(f'/meetings/{meeting.id}/copy_agenda_item')
    page.form['copy_to'] = page.form['copy_to'].options[0][0]
    page.form.submit().follow()
