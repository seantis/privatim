from tests.shared.utils import find_login_form


def test_can_login(client):
    resp = client.get('/login')
    anon_session_id = client.cookies['beaker.session.id']

    form = find_login_form(resp.forms)
    form['email'] = 'admin@example.org'
    form['password'] = 'test'
    resp = form.submit()

    assert resp.status_code == 302
    assert resp.location == 'http://localhost/'

    assert client.cookies['beaker.session.id'] != anon_session_id, \
        "Session cookie should have been renewed!"
