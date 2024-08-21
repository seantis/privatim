from privatim.models import Consultation
from tests.shared.utils import create_consultation, create_meeting


def test_filter(client):
    session = client.db
    client.login_admin()
    # Add a meeting and a consultation
    cons = create_consultation(tags=['ZH'])
    session.add(cons)

    meeting = create_meeting()
    session.add(meeting)
    session.commit()

    cons = Consultation(
        title='2nd Consultation',
        creator=client.user
    )
    session.add(cons)
    session.flush()
    session.commit()

    page = client.get('/activities')
    form = page.forms['filter_activities']
    form['consultation'] = True
    form['meeting'] = False
    form['comment'] = False
    form.submit().follow()

    page = client.get('/activities')

    assert 'Test Consultation' in page

    page = client.get('/activities')
    form = page.forms['filter_activities']
    form['consultation'] = True
    form['meeting'] = True
    form['comment'] = False
    form.submit().follow()
    page = client.get('/activities')
    assert 'Powerpoint Parade' in page

    # Test comment filter

    page = client.get(f'/consultation/{cons.id}')
    page.form['content'] = 'What an interesting thought'
    page.form.submit()
    page = client.get('/activities')
    assert 'What an interesting thought' in page

    form['consultation'] = True
    form['meeting'] = True
    form['comment'] = False
    page = form.submit().follow()
    assert 'What an interesting thought' not in page
    assert 'Test Consultation' in page
    assert '2nd Consultation' in page
    assert 'Powerpoint Parade' in page

    # Test all filters enabled
    page = client.get('/activities')
    form = page.forms['filter_activities']
    form['consultation'] = True
    form['meeting'] = True
    form['comment'] = True
    page = form.submit().follow()
    assert 'What an interesting thought' in page
    assert 'Test Consultation' in page
    assert '2nd Consultation' in page
    assert 'Powerpoint Parade' in page


def test_translation_navbar(client):
    client.login_admin()

    page = client.get('/activities')
    form = page.pyquery('form#search')[0]
    input_search = form[1]
    assert input_search.get('placeholder') == 'Volltextsuche...'
