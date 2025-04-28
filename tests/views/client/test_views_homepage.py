from privatim.models import Consultation
from tests.shared.utils import create_consultation, create_meeting


from webtest import TestApp  # type:ignore


def test_filter_activities(client: TestApp):
    session = client.db
    client.login_admin()

    # Add consultations with different statuses
    cons1 = create_consultation(
        title='Consultation Created', status='Created', tags=['ZH']
    )
    cons2 = create_consultation(
        title='Consultation In Progress', status='In Progress'
    )
    cons3 = create_consultation(
        title='Consultation Completed', status='Completed'
    )
    session.add_all([cons1, cons2, cons3])

    # Add a meeting
    meeting = create_meeting(name='Test Meeting')
    session.add(meeting)
    session.commit()

    # --- Test Type Filtering ---
    page = client.get('/activities')
    assert 'Consultation Created' in page
    assert 'Consultation In Progress' in page
    assert 'Consultation Completed' in page
    assert 'Test Meeting' in page

    # Filter: Only Consultations
    form = page.forms['filter_activities']
    form['consultation'] = True
    form['meeting'] = False
    page = form.submit().follow()
    assert 'Consultation Created' in page
    assert 'Consultation In Progress' in page
    assert 'Consultation Completed' in page
    assert 'Test Meeting' not in page

    # Filter: Only Meetings
    form = page.forms['filter_activities']
    form['consultation'] = False
    form['meeting'] = True
    page = form.submit().follow()
    assert 'Consultation Created' not in page
    assert 'Consultation In Progress' not in page
    assert 'Consultation Completed' not in page
    assert 'Test Meeting' in page

    # Filter: Both (default after GET without params, but test explicit POST)
    form = page.forms['filter_activities']
    form['consultation'] = True
    form['meeting'] = True
    page = form.submit().follow()
    assert 'Consultation Created' in page
    assert 'Consultation In Progress' in page
    assert 'Consultation Completed' in page
    assert 'Test Meeting' in page

    # --- Test Status Filtering (Consultations only) ---
    # Filter: Status 'Created'
    form = page.forms['filter_activities']
    form['consultation'] = True
    form['meeting'] = False
    form['status'] = 'Created'
    page = form.submit().follow()
    assert 'Consultation Created' in page
    assert 'Consultation In Progress' not in page
    assert 'Consultation Completed' not in page
    assert 'Test Meeting' not in page

    # Filter: Status 'In Progress'
    form = page.forms['filter_activities']
    form['consultation'] = True
    form['meeting'] = False
    form['status'] = 'In Progress'
    page = form.submit().follow()
    assert 'Consultation Created' not in page
    assert 'Consultation In Progress' in page
    assert 'Consultation Completed' not in page
    assert 'Test Meeting' not in page

    # Filter: Status 'Completed'
    form = page.forms['filter_activities']
    form['consultation'] = True
    form['meeting'] = False
    form['status'] = 'Completed'
    page = form.submit().follow()
    assert 'Consultation Created' not in page
    assert 'Consultation In Progress' not in page
    assert 'Consultation Completed' in page
    assert 'Test Meeting' not in page

    # Filter: All Statuses (empty value)
    form = page.forms['filter_activities']
    form['consultation'] = True
    form['meeting'] = False
    form['status'] = ''  # 'All Statuses' option
    page = form.submit().follow()
    assert 'Consultation Created' in page
    assert 'Consultation In Progress' in page
    assert 'Consultation Completed' in page
    assert 'Test Meeting' not in page

    # Filter: Status 'Created' and Meetings (should show only 'Created' cons)
    form = page.forms['filter_activities']
    form['consultation'] = True
    form['meeting'] = True
    form['status'] = 'Created'
    page = form.submit().follow()
    assert 'Consultation Created' in page
    assert 'Consultation In Progress' not in page
    assert 'Consultation Completed' not in page
    assert 'Test Meeting' in page # Meetings are unaffected by status filter


def test_translation_navbar(client):
    client.login_admin()

    page = client.get('/activities')
    form = page.pyquery('form#search')[0]
    input_search = form[1]
    assert input_search.get('placeholder') == 'Volltextsuche...'
