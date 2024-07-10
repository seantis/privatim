import pytest
from lxml.etree import tostring

from privatim.models import User
from privatim.models.comment import Comment
from privatim.models.consultation import Status, Consultation
from sqlalchemy import select, exists
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
    db.commit()
    db.refresh(consultation)

    page = client.get('/consultations')

    assert 'Noch keine' not in page
    assert 'Vernehmlassung zur Interkantonalen Vereinbarung über den' in page

    print(str(consultation.id))
    # page = client.get(f'/consultations/{str(consultation.id)}')


def test_view_add_and_delete_consultation(client):

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
    page.form['evaluation_result'] = 'the evaluation result'
    page.form['decision'] = 'the decision'
    page.form['status'] = '1'
    page.form['secondary_tags'] = ['AG', 'ZH']
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
    # add comment
    page = client.get(f'/consultation/{str(consultation_id)}')
    page.form['content'] = 'Comment goes here'
    page = page.form.submit().follow()
    assert 'Comment goes here' in page

    # Delete consultation
    client.get(f'/consultations/{str(consultation_id)}/delete')
    comment_exists_stmt = select(exists().where(Comment.id == consultation_id))
    comment_exists = session.scalar(comment_exists_stmt)
    assert not comment_exists

    # Check if the consultation still exists
    consultation_stmt = select(Consultation).where(
        Consultation.id == consultation_id
    )
    consultation = session.scalar(consultation_stmt)
    assert consultation is None


@pytest.mark.skip
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
    page.form['secondary_tags'] = ['AG', 'ZH']
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
    page.form['secondary_tags'] = ['BE', 'LU']

    # this is the 'Weitere Dokumente hochladen form'
    # which does not work as intended
    # todo: thi needs to select the other form for file updload and use the
    # find the right field by checking where the value is 'keep':

    # def find_replace_file_checkbox(page, radio_btn_value='replace',
    #                                add_additional_files=False):
    #     """ Find the upload file form field which is used to replace the
    #     existing file (There is another field which is used to upload more
    #     documents additionally, this may be selected
    #     with add_additional_files """
    #     assert radio_btn_value in ('keep', 'replace', 'delete')
    #     # this kind of assumes naming convention but should work for now...
    #     expected_file_form_in_page = [
    #         page.form.fields['files-1'],
    #         page.form.fields['files']
    #     ]
    #     form_index = 1 if add_additional_files else 0
    #     if add_additional_files is False:
    #         radio_options = list(expected_file_form_in_page[form_index])
    #         breakpoint()
    #
    #         checkbox = next(
    #             radio
    #             for radio in expected_file_form_in_page[0]
    #             if radio.value == radio_btn_value
    #         )
    #         # Select the radio button
    #         checkbox.select()
    #     else:
    #         checkbox = next(
    #             radio
    #             for radio in expected_file_form_in_page[1]
    #             if radio.value == radio_btn_value
    #         )
    #     return checkbox
    #
    #
    # foo = find_replace_file_checkbox(page)
    # breakpoint()

    def find_replace_file_checkbox(page):
        correct_file_form = page.form.fields['files-1']
        checkbox_replace_file = next(
            radio for radio in correct_file_form if radio.value == 'replace'
        )
        return checkbox_replace_file

    # breakpoint()
    # checkbox_replace_file = next(radio for radio in correct_file_form if
    #                              radio.value == 'replace')

    # breakpoint()
    page.form['files'] = Upload(
        'UpdatedTest.txt',
        b'Updated file ' b'content.'
    )
    page = page.form.submit().follow()
    assert page.status_code == 200

    consultation_id = session.execute(
        select(Consultation.id).filter_by(is_latest_version=1)
    ).scalar_one()
    # assert we are redirected to the edited consultation:
    assert f'consultation/{str(consultation_id)}' in page.request.url

    # navigate with id to verify the edits
    page = client.get(f'/consultation/{str(consultation_id)}')
    page.showbrowser()  # this is ok
    # todo: file link is not in page? why

    assert 'updated description' in page

    # check the file link
    href = tostring(page.pyquery('a.document-link')[0]).decode(
        'utf-8')
    href = client.extract_href(href)
    resp = client.get(href)

    assert not resp.status_code == 404
    assert resp.status_code == 200
