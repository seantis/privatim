
def test_translation_navbar(client):
    client.login_admin()

    page = client.get('/activities')
    form = page.pyquery('form#search')[0]
    input_search = form[1]
    assert input_search.get('placeholder') == 'Suchen...'

