from datetime import datetime
from sqlalchemy import select
from privatim.models import User, WorkingGroup, Meeting


def test_view_add_working_group(client):
    users = [
        User(
            email='max@example.org',
            first_name='Max',
            last_name='Müller',
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

    client.db.commit()

    client.login_admin()
    page = client.get('/working_groups/add')
    assert page.status_code == 200

    page.form['name'] = 'Test Group'
    page.form['chairman'].select(text='Max Müller (MM)')
    page.form['users'].select_multiple(
        texts=['Kurt Huber (KH)', 'Max Müller (MM)']
    )
    page = page.form.submit().follow()
    page = page.click("Test Group")

    user_list = page.pyquery('ul.generic-user-list')[0]
    assert 'Max Müller' in user_list.text_content().strip()
    assert 'Kurt Huber' in user_list.text_content().strip()

    u = User(email='a@vivaldi.org', first_name='Vintonio', last_name='Avaldi')
    client.db.add(u)
    client.db.commit()

    page = client.get('/working_groups/add')
    page.form['name'] = 'Test Group2'
    page.form['users'].select_multiple(
        texts=['Kurt Huber (KH)', 'Max Müller (MM)']
    )
    page.form['leader'].select(text='Vintonio Avaldi (VA)')
    page = page.form.submit().follow()
    page = page.click("Test Group2")

    user_list = page.pyquery('ul.generic-user-list')[0]

    assert 'Max Müller' in user_list.text_content().strip()
    assert 'Kurt Huber' in user_list.text_content().strip()
    assert 'Vintonio Avaldi' in user_list.text_content().strip()


def test_view_add_working_group_with_meeting_and_leader(client):

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
    client.db.commit()
    client.login_admin()

    page = client.get('/working_groups/add')
    assert page.status_code == 200

    page.form['name'] = 'Test Group'
    page.form['leader'].select(text='Alexa Troller (AT)')
    page.form['users'].select_multiple(
        texts=['Kurt Huber (KH)', 'Max Müller (MM)']
    )
    page = page.form.submit().follow()

    assert page.status_code == 200
    assert 'Test Group' in page

    stmt = select(WorkingGroup).where(WorkingGroup.name == 'Test Group')
    group = client.db.execute(stmt).scalars().first()
    assert group.leader.fullname == 'Alexa Troller (AT)'

    member_names = sorted({member.fullname for member in group.users})
    assert set(member_names) == {
        'Alexa Troller (AT)', 'Kurt Huber (KH)', 'Max Müller (MM)'
    }

    # test add_meeting
    page = client.get(f'/working_groups/{group.id}/add')
    page.form['name'] = 'Weekly Meeting'
    page.form['time'] = datetime.now().strftime('%Y-%m-%dT%H:%M')
    page.form['attendees'].select_multiple(
        texts=['Kurt Huber (KH)', 'Max Müller (MM)']
    )
    page = page.form.submit().follow()

    assert 'Weekly Meeting' in page

    stmt = select(Meeting).where(Meeting.working_group_id == group.id)
    meeting = client.db.execute(stmt).scalars().first()
    assert 'Weekly Meeting' in page

    page = client.get(f'/meetings/{meeting.id}/delete').follow()
    assert 'erfolgreich gelöscht' in page


def test_view_delete_working_group_with_meetings(client):
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
    client.db.commit()
    client.login_admin()

    page = client.get('/working_groups/add')
    assert page.status_code == 200

    page.form['name'] = 'Test Group'
    page.form['leader'].select(text='Alexa Troller (AT)')
    page.form['users'].select_multiple(
        texts=['Kurt Huber (KH)', 'Max Müller (MM)']
    )
    page = page.form.submit().follow()

    assert page.status_code == 200
    assert 'Test Group' in page

    stmt = select(WorkingGroup).where(WorkingGroup.name == 'Test Group')
    group = client.db.execute(stmt).scalars().first()
    assert group.leader.fullname == 'Alexa Troller (AT)'

    page = client.get(f'/working_groups/{group.id}/add')
    page.form['name'] = 'Weekly Meeting'
    page.form['time'] = datetime.now().strftime('%Y-%m-%dT%H:%M')
    page.form['attendees'].select_multiple(
        texts=['Kurt Huber (KH)', 'Max Müller (MM)']
    )
    page = page.form.submit().follow()

    assert 'Weekly Meeting' in page

    stmt = select(Meeting).where(Meeting.working_group_id == group.id)
    meeting = client.db.execute(stmt).scalars().first()
    assert meeting.name == 'Weekly Meeting'

    # Attempt to delete the working group
    page = client.get(f'/working_groups/{group.id}/delete').follow()
    assert (
        'kann nicht gelöscht werden' in page
    )

    # Delete the meeting
    page = client.get(f'/meetings/{meeting.id}/delete').follow()
    assert 'erfolgreich gelöscht' in page

    # Attempt to delete the working group again
    page = client.get(f'/working_groups/{group.id}/delete').follow()
    assert 'erfolgreich gelöscht' in page

    # Verify the working group is deleted
    stmt = select(WorkingGroup).where(WorkingGroup.name == 'Test Group')
    group = client.db.execute(stmt).scalars().first()
    assert group is None


def test_edit_working_group(client):
    kurt = User(
        email='kurt@example.org',
        first_name='Kurt',
        last_name='Huber',
    )
    maxm = User(
        email='max@example.org',
        first_name='Max',
        last_name='Müller',
    )
    users = [kurt, maxm]
    for user in users:
        user.set_password('test')
        client.db.add(user)

    client.db.commit()
    session = client.db
    client.login_admin()

    # Create a new working group
    page = client.get('/working_groups/add')
    page.form['name'] = 'TestXY'
    page.form['chairman'].select(text='Max Müller (MM)')
    page.form['leader'].select(text='Max Müller (MM)')
    page.form['users'].select_multiple(
        texts=['Kurt Huber (KH)', 'Max Müller (MM)']
    )
    page = page.form.submit().follow()
    page = page.click('TestXY')
    for name in ['Kurt Huber (KH)', 'Max Müller (MM)']:
        assert name in page

    group = session.execute(select(WorkingGroup)).unique().scalar_one()
    assert group.name == 'TestXY'
    assert group.chairman == maxm
    assert group.leader == maxm
    assert group.chairman == maxm

    # Get the id of the newly created working group
    group_id = session.execute(select(WorkingGroup.id)).scalar_one()

    # Edit the working group
    page = client.get(f'/working_groups/edit/{group_id}')

    page.form['name'] = 'Updated Working Group'
    page.form['chairman'].select(text='Kurt Huber (KH)')
    page.form['leader'].select(text='Kurt Huber (KH)')
    page.form['users'].select_multiple(texts=['Max Müller (MM)'])
    page = page.form.submit().follow()

    assert page.status_code == 200

    # Verify the changes in the database
    session.reset()
    stmt = select(WorkingGroup).where(WorkingGroup.id == group_id)
    updated_group = session.execute(stmt).unique().scalar_one()
    updated_group = session.execute(select(WorkingGroup)).unique().scalar_one()

    assert updated_group.name == 'Updated Working Group'
    assert updated_group.chairman.email == 'kurt@example.org'
    assert updated_group.leader.email == 'kurt@example.org'
    assert updated_group.chairman.email == 'kurt@example.org'

    # Check if the changes are reflected on the page
    page = client.get(f'/working_groups/{group_id}/meetings/')
    assert 'Updated Working Group' in page
    assert 'Kurt Huber (KH)' in page
    assert 'Max Müller (MM)' in page
