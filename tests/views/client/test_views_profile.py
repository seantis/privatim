from webtest.forms import Upload


def test_profile(client):
    client.login_admin()
    page = client.get('/profile')

    page.form['profilePic'] = Upload('Test.txt', b'Test')
    page = page.form.submit().follow()
    assert page.status_code == 200
