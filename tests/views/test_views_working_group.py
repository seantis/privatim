from privatim.models import User


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

    page = client.get('/groups/add')

    page.form['name'] = 'Test Group'
    page.form['leader'].select(text='Alexa Troller')
    page.form['members'].select_multiple(texts=['Kurt Huber', 'Max Müller'])
    page.form.submit()
