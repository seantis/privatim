from privatim.models import User, SearchableFile
from privatim.models.comment import Comment
from privatim.models.consultation import Status, Consultation
from sqlalchemy import select, exists, func
from webtest.forms import Upload

from privatim.views.consultations import delete_consultation_chain


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

    href = page.pyquery('a.document-link')[0].get('href')
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


def test_edit_consultation_with_files(client, pdf_vemz):

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
    page.form['files'] = Upload(*pdf_vemz)
    page = page.form.submit().follow()

    consultation = session.execute(
        select(Consultation).filter_by(description='the description')
    ).scalar_one()
    assert (
        'datenschutzbeauftragt'
        in consultation.searchable_text_de_CH
    )

    # assert we are redirected to the just created consultation:
    consultation_id = consultation.id
    assert f'consultation/{str(consultation_id)}' in page.request.url

    # navigate to the edit page
    page = client.get(f'/consultations/{str(consultation_id)}/edit')

    # edit the consultation
    page.form['title'] = 'updated title'
    page.form['description'] = 'updated description'
    page.form['recommendation'] = 'updated recommendation'
    page.form['status'] = '2'
    page.form['secondary_tags'] = ['BE', 'LU']

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
    assert f'consultation/{str(consultation_id)}' in page.request.url
    page = client.get(f'/consultation/{str(consultation_id)}')
    assert 'updated description' in page

    # check the file link
    href = page.pyquery('a.document-link')[0].get('href')
    resp = client.get(href)
    assert resp.status_code == 200


def test_edit_consultation_without_files(client):

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
    page.form.submit().follow()

    consultation_id = session.execute(
        select(Consultation.id).filter_by(is_latest_version=1)
    ).scalar_one()

    # add a comment
    page = client.get(f'/consultation/{str(consultation_id)}')
    page.form['content'] = 'Comment'
    page.form.submit()

    page = client.get(f'/consultations/{str(consultation_id)}/edit')

    # edit the consultation
    page.form['title'] = 'updated title'
    page.form['description'] = 'updated description'
    page.form['recommendation'] = 'updated recommendation'
    page.form['evaluation_result'] = 'evaluation result'
    page.form['decision'] = 'decision'
    page.form['status'] = '2'
    page.form['secondary_tags'] = ['BE', 'LU']
    page = page.form.submit().follow()
    assert page.status_code == 200

    stmt = select(Consultation).where(Consultation.is_latest_version == 1)
    assert len(session.scalars(stmt).all()) == 1

    # test versioning
    with session.no_consultation_filter():
        count = session.scalar(
            select(func.count())
            .select_from(Consultation)
            .where(Consultation.is_latest_version == 0)
        )
    assert count == 1

    consultation_id = session.execute(
        select(Consultation.id).filter_by(is_latest_version=1)
    ).scalar_one()
    assert f'consultation/{str(consultation_id)}' in page.request.url

    client.get(f'/consultation/{str(consultation_id)}')

    # After editing the comment should still be visible
    assert page.pyquery('p.comment-text')[0].text.strip() == 'Comment'

    text_paragraph = [
        e.text_content().strip() for e in page.pyquery(
            '.consultation-text-paragraph')
    ]
    assert 'updated title' in page
    assert 'updated description' in text_paragraph[0]
    assert 'updated recommendation' in text_paragraph[1]
    assert 'evaluation result' in text_paragraph[2]
    assert 'decision' in text_paragraph[3]

    assert 'BE' in page
    assert 'LU' in page


def get_files_by_filename(session, filenames):
    with session.no_consultation_filter():
        query = (
            select(SearchableFile)
            .filter(
                SearchableFile.filename.in_(filenames),
            )
        )
        result = session.execute(query)
        files = result.scalars().all()
        found_files = {file.filename: file for file in files}
        # missing_files = set(filenames) - set(found_files.keys())
        return found_files


def test_edit_and_delete_consultation_chain(client, pdf_vemz):
    session = client.db
    client.login_admin()

    # Create a new consultation
    page = client.get('/consultations')
    page = page.click('Vernehmlassung Erfassen')
    page.form['title'] = 'Initial Consultation'
    page.form['description'] = 'Initial description'
    page.form['recommendation'] = 'Initial recommendation'
    page.form['status'] = '1'
    page.form['secondary_tags'] = ['AG', 'ZH']
    page.form['files'] = Upload(*pdf_vemz)
    page.form.submit().follow()

    initial_consultation = session.execute(
        select(Consultation).filter_by(description='Initial description')
    ).scalar_one()
    initial_id = initial_consultation.id

    # Edit the consultation to create a new version
    page = client.get(f'/consultations/{str(initial_id)}/edit')
    page.form['title'] = 'Updated Consultation'
    page.form['description'] = 'Updated description'
    page.form['recommendation'] = 'Updated recommendation'
    page.form['status'] = '2'
    page.form['secondary_tags'] = ['BE', 'LU']
    page.form['files'] = Upload('UpdatedTest.txt',
                                b'Updated file content.')
    page.form.submit().follow()

    # check files exisit query
    # filename1 = 'search_test_privatim_Vernehmlassung_VEMZ.pdf'
    # filename2 = 'UpdatedTest.txt'

    # assert (
    #     'search_test_privatim_Vernehmlassung_VEMZ.pdf' in files
    # ), "Expected file not found"
    # assert 'UpdatedTest.txt' in files, "Expected file not found"

    updated_consultation = session.execute(
        select(Consultation).filter_by(is_latest_version=1)
    ).scalar_one()
    updated_id = updated_consultation.id

    # # Verify the chain
    with session.no_consultation_filter():
        initial_consultation = session.execute(
            select(Consultation).filter_by(is_latest_version=0)
        ).scalar_one()
        updated_consultation = session.execute(
            select(Consultation).filter_by(is_latest_version=1)
        ).scalar_one()

        # assert initial_consultation.replaced_by == updated_consultation
        assert updated_consultation.previous_version == initial_consultation

    # Delete the consultation chain
    deleted_ids = delete_consultation_chain(session, updated_consultation)

    # Verify deletions
    assert len(deleted_ids) == 2
    assert initial_id in deleted_ids
    assert updated_id in deleted_ids

    # Verify consultations no longer exist in the database

    with session.no_consultation_filter():
        assert not session.query(Consultation).count()
        # Verify related Status objects have been deleted
        assert session.execute(select(Status).filter(
            Status.consultation_id.in_(deleted_ids))).first() is None
