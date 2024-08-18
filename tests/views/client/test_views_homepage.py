from privatim.models import Consultation
from tests.shared.utils import create_consultation, create_meeting


def test_filter(client):
    session = client.db
    client.login_admin()
    cons = create_consultation(tags=['ZH'])
    session.add(cons)

    meeting = create_meeting()
    session.add(meeting)
    session.commit()

    # test the filter by tags (cantons)
    # this one has no tags, should not appear in filter
    cons = Consultation(
        title='2nd Consultation',
        creator=client.user
    )
    session.add(cons)
    session.flush()
    session.commit()

    page = client.get('/activities')
    form = page.forms['filter_activities']
    form['canton'] = 'ZH'
    form['consultation'] = True
    form['meeting'] = False
    form['comment'] = False
    page = form.submit().follow()

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


def test_translation_navbar(client):
    client.login_admin()

    page = client.get('/activities')
    form = page.pyquery('form#search')[0]
    input_search = form[1]
    assert input_search.get('placeholder') == 'Volltextsuche...'
