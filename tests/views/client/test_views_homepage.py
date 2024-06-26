def test_view_activities(client):
    client.login_admin()

    page = client.get('/activities')
    assert page.status_code == 200
    assert 'Aktivitäten' in page.text

    # fill out the search form
    client.skip_n_forms = False
    form = page.forms[0]
    print(form.fields)

    form['search'] = 'My search'
    page = form.submit()
