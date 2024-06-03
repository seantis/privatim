from datetime import datetime
from sqlalchemy import select

from privatim.models import User, WorkingGroup


def test_view_add_working_group_with_meeting(client):

    users = [
        User(
            email='max@example.org',
            first_name='Max',
            last_name='Müller',
        ),
        User(
            email='alexa@example.org',
            first_name='Alexa',
            last_name='Troller',
        ),
        User(
            email='kurt@example.org',
            first_name='Kurt',
            last_name='Huber',
        ),
    ]
    for user in users:
        user.set_password('test')
        client.db.add(user)
    client.db.flush()
    client.login_admin()

    page = client.get('/working_groups/add')
    assert page.status_code == 200

    page.form['name'] = 'Test Group'
    page.form['leader'].select(text='Alexa Troller')
    page.form['members'].select_multiple(texts=['Kurt Huber', 'Max Müller'])
    page = page.form.submit().follow()

    assert page.status_code == 200
    assert 'Test Group' in page

    stmt = select(WorkingGroup).where(WorkingGroup.name == 'Test Group')
    group = client.db.execute(stmt).scalars().first()
    assert group.leader.fullname == 'Alexa Troller'

    member_names = {member.fullname for member in group.users}
    assert member_names == {'Kurt Huber', 'Max Müller'}
    assert isinstance(group.id, str)

    # test add_meeting
    page = client.get(f'/working_groups/{group.id}/add')
    page.form['name'] = 'Weekly Meeting'
    page.form['time'] = datetime.now().strftime('%Y-%m-%dT%H:%M')
    page.form['attendees'].select_multiple(texts=['Kurt Huber', 'Max Müller'])
    page = page.form.submit().follow()

    assert 'Weekly Meeting' in page
