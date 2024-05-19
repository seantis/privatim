from sqlalchemy import select

from privatim.models import User, WorkingGroup


def test_view_add_working_group(client):

    users = [
        User(
            email='max@example.org',
            password='test',  # nosec: B106
            first_name='Max',
            last_name='Müller',
        ),
        User(
            email='alexa@example.org',
            password='test',  # nosec: B106
            first_name='Alexa',
            last_name='Troller',
        ),
        User(
            email='kurt@example.org',
            password='test',  # nosec: B106
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
    return

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
