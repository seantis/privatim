from privatim.models import Tag, Consultation
from shared.utils import create_consultation, create_meeting


def test_filter(client):
    session = client.db
    client.login_admin()

    tags = [
        Tag(name='ZH'),
    ]
    cons = create_consultation(tags=tags)
    session.add(cons)
    session.commit()

    meeting = create_meeting()
    session.add(meeting)
    session.commit()

    page = client.get('/activities')
    form = page.forms['filter_activities']
    form['canton'] = 'ZH'
    form['consultation'] = True
    form['meeting'] = False
    form['comment'] = False
    page = form.submit()
    assert 'Test Consultation' in page

    # filter by tags
    tags = []
    # this one has no tags, should not appear in filter
    cons = Consultation(
        title='2nd Consultation',
        creator=client.user
    )
    session.add(cons)
    session.commit()

    page = client.get('/activities')
    form = page.forms['filter_activities']
    form['canton'] = 'ZH'
    form['consultation'] = True
    form['meeting'] = False
    form['comment'] = False
    page = form.submit()

    assert '2nd Consultation' in page
    assert 'Test Consultation' not in page


def test_translation_navbar(client):
    client.login_admin()

    page = client.get('/activities')
    form = page.pyquery('form#search')[0]
    input_search = form[1]
    assert input_search.get('placeholder') == 'Suchen...'

