def test_filter(client):
    client.login_admin()

    page = client.get('/activities')
    form = page.forms['filter_activities']
    breakpoint()
