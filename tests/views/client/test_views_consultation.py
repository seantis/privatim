from sqlalchemy.orm import selectinload, undefer

from privatim.cli.print_trees import print_consultation_tree
from privatim.models import User, SearchableFile
from privatim.models.comment import Comment
from privatim.models.consultation import Consultation
from sqlalchemy import select, exists, func
from webtest.forms import Upload

from privatim.utils import get_previous_versions


def test_view_consultation(client):

    client.login_admin()
    db = client.db

    # add a consultations:
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
        status='Erstellt',
        creator=User(email='test@foo.com')
    )
    db.add(consultation)
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
    page.form['status'] = 'Created'
    page.form['secondary_tags'] = ['AG', 'ZH']
    page.form['files'] = Upload('Test.txt', b'File content.')
    page = page.form.submit().follow()

    consultation = session.execute(
        select(Consultation)
        .options(selectinload(Consultation.files))
        .filter_by(description='the description')
    ).scalar_one()
    consultation_id = consultation.id

    searchable_file = consultation.files[0]
    searchable_file: SearchableFile
    assert searchable_file.content_type == 'text/plain'

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

    # test file deleted
    searchable_file_stmt = select(SearchableFile).where(
        SearchableFile.id == searchable_file.id
    )
    assert session.scalar(searchable_file_stmt) is None


def test_edit_consultation_with_files(client, pdf_vemz, pdf_full_text):

    session = client.db
    client.login_admin()

    # Create a new consultation
    page = client.get('/consultations')
    page = page.click('Vernehmlassung Erfassen')
    page.form['title'] = 'test'
    page.form['description'] = 'the description'
    page.form['recommendation'] = 'the recommendation'
    page.form['secondary_tags'] = ['AG', 'ZH']
    page.form['files'] = Upload(*pdf_vemz)
    page = page.form.submit().follow()

    added_consultation = session.execute(
        select(Consultation)
        .options(selectinload(Consultation.files))
        .filter_by(description='the description')
    ).scalar_one()

    updated_file = added_consultation.files[0]
    assert (
        'datenschutzbeauftragt'
        in updated_file.searchable_text_de_CH
    )
    assert ('Verordnung über den Einsatz elektronischer Mittel' in
            updated_file.extract)

    # assert we are redirected to the just created consultation:
    consultation_id = added_consultation.id
    assert f'consultation/{str(consultation_id)}' in page.request.url

    # navigate to the edit page
    page = client.get(f'/consultations/{str(consultation_id)}/edit')

    # edit the consultation
    page.form['title'] = 'updated title'
    page.form['description'] = 'updated description'
    page.form['recommendation'] = 'updated recommendation'
    page.form['secondary_tags'] = ['BE', 'LU']
    # the file form is a little bit more complex, as there is also the
    # associated radio button for 'keep', 'delete', 'replace'. But,
    # this is just adding more files, not modifying anything
    page.form['files'] = Upload(*pdf_full_text)
    page = page.form.submit().follow()
    assert page.status_code == 200

    updated_consultation = session.execute(
        select(Consultation)
        .options(
            selectinload(Consultation.files).options(
                undefer(SearchableFile.extract)
            )
        )
        .filter_by(is_latest_version=1)
    ).scalar_one()

    consultation_id = updated_consultation.id
    assert updated_consultation.title == 'updated title'
    assert updated_consultation.description == 'updated description'
    assert updated_consultation.recommendation == 'updated recommendation'

    updated_file = next(
        (f for f in updated_consultation.files
         if f.filename == 'fulltext_search.pdf'),
        None
    )
    assert 'full' in updated_file.searchable_text_de_CH
    assert 'text' in updated_file.searchable_text_de_CH
    assert 'full text search' in updated_file.extract

    assert f'consultation/{str(consultation_id)}' in page.request.url
    page = client.get(f'/consultation/{str(consultation_id)}')
    assert 'updated description' in page

    # check the file link
    href = page.pyquery('a.document-link')[0].get('href')
    resp = client.get(href)
    assert resp.status_code == 200

    with session.no_consultation_filter():
        # Ensure we're working with a clean session
        session.expunge_all()

        # Fetch both consultations
        consultations = session.execute(
            select(Consultation)
            .options(
                selectinload(Consultation.replaced_by),
                selectinload(Consultation.previous_version),
            )
        ).scalars().all()

        # there should be a total 2 Consultation objects in the db
        assert len(consultations) == 2, (
            "Expected 2 consultations, got {}").format(
            len(consultations)
        )

        # Sort consultations by is_latest_version (1 should be the
        # newer version)
        consultations.sort(key=lambda c: c.is_latest_version, reverse=True)
        newer, older = consultations

        print(f"Newer consultation: {newer}")
        print(f"Older consultation: {older}")

        print(f"Newer previous_version: {newer.previous_version}")
        print(f"Older replaced_by: {older.replaced_by}")

        assert newer.previous_version == older
        assert older.replaced_by == newer

        # Check if the relationships are properly set in the database
        session.refresh(newer)
        session.refresh(older)

        assert newer.previous_version == older
        assert older.replaced_by == newer


def test_edit_consultation_without_files(client):

    session = client.db
    client.login_admin()

    # Create a new consultation
    page = client.get('/consultations')
    page = page.click('Vernehmlassung Erfassen')
    page.form['title'] = 'test'
    page.form['description'] = 'the description'
    page.form['recommendation'] = 'the recommendation'
    page.form['status'] = 'Created'
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
    page.form['status'] = 'In Progress'
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


def test_consultation_delete(client, pdf_vemz):

    session = client.db
    client.login_admin()

    # Create a new consultation
    page = client.get('/consultations')
    page = page.click('Vernehmlassung Erfassen')
    page.form['title'] = 'test'
    page.form['description'] = 'the description'
    page.form['recommendation'] = 'the recommendation'
    page.form['status'] = 'Created'
    page.form['secondary_tags'] = ['AG', 'ZH']
    filename, contet = pdf_vemz
    page.form['files'] = Upload(filename=filename, content=contet)
    page = page.form.submit().follow()

    consultation = session.execute(
        select(Consultation)
        .options(selectinload(Consultation.files))
        .filter_by(description='the description')
    ).scalar_one()

    updated_file = consultation.files[0]
    assert (
            'datenschutzbeauftragt'
            in updated_file.searchable_text_de_CH
    )
    assert ('Verordnung über den Einsatz elektronischer Mittel' in
            updated_file.extract)

    # assert we are redirected to the just created consultation:
    consultation_id = consultation.id
    assert f'consultation/{str(consultation_id)}' in page.request.url

    # navigate to the edit page
    page = client.get(f'/consultations/{str(consultation_id)}/edit')

    # edit the consultation
    page.form['title'] = 'updated title'
    page.form['description'] = 'updated description'
    page.form['recommendation'] = 'updated recommendation'
    page.form['status'] = 'In Progress'
    page.form['secondary_tags'] = ['BE', 'LU']
    page.form['files'] = Upload(
        'UpdatedTest.txt',
        b'Updated file ' b'content.'
    )
    page = page.form.submit().follow()
    assert page.status_code == 200

    consultation = session.execute(
        select(Consultation)
        .filter_by(description='updated description')
    ).scalar_one()

    latest_id = consultation.id
    page = client.get(f'/consultation/{latest_id}')
    page.form['content'] = 'Comment is here'
    page = page.form.submit().follow()
    assert page.status_code == 200

    # Delete:
    page = client.get(f'/consultations/{latest_id}/delete')
    page = page.follow()
    assert 'Vernehmlassung in den Papierkorb verschoben' in page

    consultation = session.execute(
        select(Consultation)
        .filter_by(description='updated description')
    ).scalar_one_or_none()
    assert consultation is None

    # but it is still in db, just soft deleted:
    with session.no_soft_delete_filter():
        consultation = session.execute(
            select(Consultation)
            .filter_by(description='updated description')
        ).scalar_one_or_none()

        assert consultation.deleted

    page = client.get('/consultations')
    assert 'updated description' not in page

    # Restore from trash
    page = client.get('/trash')
    page = page.click('Wiederherstellen').follow()
    assert 'Element erfolgreich wiederhergestellt' in page

    page = client.get('/consultations')
    assert 'updated description' in page

    session.refresh(consultation)
    assert not consultation.deleted


def test_consultation_version_chain_restore(client, pdf_vemz):
    session = client.db
    client.login_admin()

    # Create initial consultation
    page = client.get('/consultations')
    page = page.click('Vernehmlassung Erfassen')
    page.form['title'] = 'original title'
    page.form['description'] = 'original description'
    page.form['status'] = 'Created'
    filename, content = pdf_vemz
    page.form['files'] = Upload(filename=filename, content=content)
    page = page.form.submit().follow()

    with session.no_consultation_filter():
        # Get the original consultation
        consultation = session.execute(
            select(Consultation)
            .options(
                selectinload(Consultation.previous_version),
                selectinload(Consultation.replaced_by)
            )
            .filter_by(description='original description')
        ).scalar_one()
        original_id = consultation.id

    # First edit
    page = client.get(f'/consultations/{str(original_id)}/edit')
    page.form['title'] = 'first update'
    page.form['description'] = 'first update description'
    page.form['status'] = 'In Progress'
    page = page.form.submit().follow()

    with session.no_consultation_filter():
        # Get the first update
        first_update = session.execute(
            select(Consultation)
            .options(
                selectinload(Consultation.previous_version),
                selectinload(Consultation.replaced_by)
            )
            .filter_by(description='first update description')
        ).scalar_one()

        # validate chain relationships
        original = first_update.previous_version

        session.refresh(original) #  this is required... why?
        assert original.is_latest() is False
        assert first_update.previous_version.id == original_id
        assert first_update.is_latest() is True
        # assert original.replaced_by.id == first_update_id



def test_display_previous_versions(client):
    # Create a user that will be reused
    session = client.db
    client.login_admin()
    user = User(email='testuser@example.org')
    session.add(user)
    session.flush()

    # create 3 consultation
    num_versions = 3
    page = client.get('/consultations')
    page = page.click('Vernehmlassung Erfassen')
    page.form['title'] = 'My Cons 0'
    page = page.form.submit().follow()

    for i in range(num_versions - 1):
        page = page.click('Bearbeiten')
        page.form['title'] = f'My Cons {i+1}'
        page = page.form.submit().follow()

    # Assert they were created
    with session.no_consultation_filter():
        consultations = (
            session.execute(
                (select(Consultation).order_by(Consultation.created.asc()))
            )
            .scalars()
            .all()
        )
    titles = [c.title for c in consultations]
    assert ['My Cons 0', 'My Cons 1', 'My Cons 2'] == titles
    assert len(consultations) == 3

    # Test get_previous_version separately
    latest = [c for c in consultations if c.is_latest_version][0]
    # Get the previous versions of latest
    previous_versions = get_previous_versions(session, latest)
    assert len(previous_versions) == num_versions - 1
    for i in range(len(previous_versions) - 1):
        assert previous_versions[i].created >= previous_versions[i + 1].created

    # test the view
    page = client.get(f'/consultation/{latest.id}')
    page.pyquery('.previous-versions')

    # check author is set in previous versions
    assert 'John Doe' in ''.join(
        e.text_content().strip() for e in page.pyquery('ul.previous-versions')
    )
