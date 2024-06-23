from lxml.etree import tostring

from privatim.models import User
from privatim.models.consultation import Status, Consultation
from sqlalchemy import select
from webtest.forms import Upload


def test_view_consultation(client):

    client.login_admin()
    db = client.db

    # add a consultations:
    status = Status(name='Erstellt')
    consultation = Consultation(
        title='Vernehmlassung zur Interkantonalen Vereinbarung über den '
              'Datenaustausch zum Betrieb gemeinsamer Abfrageplattformen  ',
        description='Stellungnahme von privatim, Konferenz der '
                    'schweizerischen Datenschutzbeauftragten, zum Entwurf '
                    'einer Interkantonalen Vereinbarung über den '
                    'Datenaustausch zum Betrieb gemeinsamer '
                    'Abfrageplattformen, zu welcher die Konferenz der '
                    'Kantonalen Justiz- und Polizeidirektorinnen und '
                    '–direktoren (KKJPD) zur Zeit eine Vernehmlassung '
                    'durchführt.',
        recommendation='Aus verfassungs- und datenschutzrechtlicher Sicht '
        'ergeben sich einerseits grundsätzliche; Vorbehalte '
        'und andererseits Hinweise zu einzelnen Bestimmungen des '
                       'Vereinbarungsentwurfs...',
        status=status,
        creator=User(email='test@foo.com')
    )
    db.add(consultation)
    db.add(status)
    db.flush()
    db.refresh(consultation)

    page = client.get('/consultations')

    assert 'Noch keine' not in page
    assert 'Vernehmlassung zur Interkantonalen Vereinbarung über den' in page

    print(str(consultation.id))
    # page = client.get(f'/consultations/{str(consultation.id)}')


def test_view_add_consultation(client):

    session = client.db
    client.login_admin()
    # test without document upload
    page = client.get('/consultations')
    page = page.click('Vernehmlassung Erfassen')
    page.form['title'] = 'test'
    page.form.submit()

    # now with all fields
    page = client.get('/consultations')
    page = page.click('Vernehmlassung Erfassen')
    page.form['title'] = 'test'
    page.form['description'] = 'the description'
    page.form['recommendation'] = 'the recommendation'
    page.form['status'] = '1'
    page.form['cantons'] = ['AG', 'ZH']
    page.form['files'] = Upload('Test.txt', b'File content.')
    page = page.form.submit().follow()

    consultation_id = session.execute(
        select(Consultation.id).filter_by(description='the description')
    ).scalar_one()

    # assert we are redirected to the just created consultation:
    assert f'consultation/{str(consultation_id)}' in page.request.url

    # navigate with id (page.click is very flaky)
    page = client.get(f'/consultation/{str(consultation_id)}')

    assert 'the description' in page
    assert 'Test.txt' in page
    href = tostring(page.pyquery('a.document-link')[0]).decode(
        'utf-8')
    href = client.extract_href(href)
    resp = client.get(href)

    assert not resp.status_code == 404
    assert resp.status_code == 200

    status_text_badge = page.pyquery('span.badge.rounded-pill')[0].text
    assert status_text_badge == 'Erstellt'


def test_view_edit_consultation(client):

    session = client.db
    client.login_admin()

    # Create a new consultation
    page = client.get('/consultations')
    page = page.click('Vernehmlassung Erfassen')
    page.form['title'] = 'test'
    page.form['description'] = 'the description'
    page.form['recommendation'] = 'the recommendation'
    page.form['status'] = '1'
    page.form['cantons'] = ['AG', 'ZH']
    page.form['files'] = Upload('Test.txt', b'File content.')
    page = page.form.submit().follow()

    consultation_id = session.execute(
        select(Consultation.id).filter_by(description='the description')
    ).scalar_one()

    # assert we are redirected to the just created consultation:
    assert f'consultation/{str(consultation_id)}' in page.request.url

    # navigate to the edit page
    page = client.get(f'/consultations/{str(consultation_id)}/edit')

    # edit the consultation
    page.form['title'] = 'updated title'
    page.form['description'] = 'updated description'
    page.form['recommendation'] = 'updated recommendation'
    page.form['status'] = '2'
    page.form['cantons'] = ['BE', 'LU']
    page.form['files'] = Upload(
        'UpdatedTest.txt',
        b'Updated file ' b'content.'
    )
    page = page.form.submit().follow()

    # assert we are redirected to the edited consultation:
    # assert f'consultation/{str(consultation_id)}' in page.request.url

    # navigate with id to verify the edits
    page = client.get(f'/consultations/{str(consultation_id)}')

    assert 'updated description' in page
    assert 'UpdatedTest.txt' in page
    href = tostring(page.pyquery('a.document-link')[0]).decode(
        'utf-8')
    href = client.extract_href(href)
    resp = client.get(href)

    assert not resp.status_code == 404
    assert resp.status_code == 200

    status_text_badge = page.pyquery('span.badge.rounded-pill')[0].text
    assert status_text_badge == 'Updated'
