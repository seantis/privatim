

def test_view_add_working_group(client):

    client.login_admin()
    page = client.get('/groups/add')
    assert page.form
