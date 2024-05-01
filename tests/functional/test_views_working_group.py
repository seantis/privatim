from webtest import TestApp


def test_view_add_working_group(webtest: TestApp, user_webtest):

    resp = webtest.get('/login')

    resp.form['email'] = 'admin@example.org'
    resp.form['password'] = 'test'
    resp = resp.form.submit()
    assert resp.status_code == 302

    resp = webtest.get('/groups/add')
    assert resp.forms
