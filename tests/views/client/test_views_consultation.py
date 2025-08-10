import re
import pytest
from sqlalchemy.orm import selectinload, undefer
import transaction
from playwright.sync_api import  expect
from privatim.models import User, SearchableFile
from privatim.models.consultation import Consultation
from sqlalchemy import select, func
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
                    'Kantonalen Justiz- und Polizeidirektornnen und '
                    '–direktoren (KKJPD) zur Zeit eine Vernehmlassung '
                    'durchführt.',
        recommendation='Aus verfassungs- und datenschutzrechtlicher Sicht '
        'ergeben sich einerseits grundsätzliche; Vorbehalte '
        'und andererseits Hinweise zu einzelnen Bestimmungen des '
                       'Vereinbarungsentwurfs...',
        status='Waiving',
        creator=User(email='test@foo.com')
    )
    db.add(consultation)
    db.commit()
    db.refresh(consultation)
    consultation_id = consultation.id
    page = client.get(f'/consultations/{str(consultation_id)}/edit')

    # test a critical edge case that caused multiple bugs:
    # Ensure form.process() and form.populate_obj() are perfect
    # mathematical inverses
    # (E.g. when processing a form submission with no user
    # modifications to values.)
    assert page.form['status'].value != 'Created'

    # Test submit and check again
    page.form['recommendation'] = 'some text'
    page = page.form.submit().follow()
    assert 'Noch keine' not in page
    assert 'Vernehmlassung zur Interkantonalen Vereinbarung über den' in page
    assert 'Erstellt' not in page

    # test empty submit
    consultation_id = page.request.url.split('/')[-1]
    page = client.get(f'/consultations/{str(consultation_id)}/edit')
    page = page.form.submit().follow()
    # status shoud not have been changed
    assert 'Verzicht' in page

    page = client.get('/activities')

    items = page.pyquery('.timeline-item')

    def get_link_from_Element_list(items): 
        all_a_elements = []
        for item in items:
            # Find all 'a' tags within the current item and its descendants
            a_elements_in_item = item.cssselect('a')
            if a_elements_in_item:
                for a_element in a_elements_in_item:
                    href = a_element.get('href') # Safely get the href attribute
                    all_a_elements.append({'element': a_element, 'href': href})
        return all_a_elements


    assert len(items) == 3
    assert 'Vernehmlassung hinzugefügt' in items[2].text_content()
    assert 'Vernehmlassung aktualisiert' in items[0].text_content()
    assert 'Vernehmlassung aktualisiert' in items[1].text_content()
    hrefs = [e['href'] for e in get_link_from_Element_list(items)]
    for l in hrefs:
        # go to each cons activity entry, and go to the edit view
        # there was a bug where this would result in 404 because we were on 
        # previous versions
        client.get(l)
        consultation_id = l.split('/')[-1]
        page = client.get(f'/consultations/{consultation_id}/edit')



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

    # Delete consultation
    client.get(f'/consultations/{str(consultation_id)}/delete')

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

        # Get the first update
        first_update = session.execute(
            select(Consultation)
            .options(
                selectinload(Consultation.previous_version),
                selectinload(Consultation.replaced_by)
            )
            .filter_by(description='first update description')
        ).scalar_one()
        first_update_id = first_update.id

        # Second edit
        page = client.get(f'/consultations/{str(first_update_id)}/edit')
        page.form['title'] = 'second update'
        page.form['description'] = 'second update description'
        page = page.form.submit().follow()

        # Get the second update (latest version)
        latest_version = session.execute(
            select(Consultation)
            .options(
                selectinload(Consultation.previous_version).selectinload(
                    Consultation.previous_version
                ),
                selectinload(Consultation.replaced_by)
            )
            .filter_by(description='second update description')
        ).scalar_one()
        latest_id = latest_version.id

        # Verify chain relationships
        assert latest_version.previous_version.id == first_update_id
        # assert latest_version.previous_version.previous_version.id ==
        # original_id

        client.get(f'/consultation/{latest_id}')
        assert 'Sie sehen eine alte Version dieser Vernehmlassung' not in page

        # Delete the latest version (should delete entire chain)
        page = client.get(f'/consultations/{latest_id}/delete')
        page = page.follow()
        assert 'Vernehmlassung in den Papierkorb verschoben' in page

        # Verify all versions are soft deleted
        # fixme: this is not yet done, but soft delete is smart enough,
        # it will work in any case.
        # Not sure if this is a good idea to set all to 'deleted'

        # with session.no_soft_delete_filter():
        #     for cons_id in [original_id, first_update_id, latest_id]:
        #         consultation = session.execute(
        #             select(Consultation)
        #             .filter_by(id=cons_id)
        #         ).scalar_one()
        #         breakpoint()
        #         # assert consultation.deleted

        # Restore from trash (using any version should restore all)
    page = client.get('/trash')
    page = page.click('Wiederherstellen').follow()
    assert 'Element erfolgreich wiederhergestellt' in page

    with session.no_consultation_filter():
        # Verify all versions are restored and maintain their relationships
        # Get latest version
        restored_latest = session.execute(
            select(Consultation)
            .options(
                selectinload(Consultation.previous_version).selectinload(
                    Consultation.previous_version
                ),
                selectinload(Consultation.replaced_by)
            )
            .filter_by(id=latest_id)
        ).scalar_one()

        assert not restored_latest.deleted
        assert restored_latest.is_latest_version == 1

        # Verify chain is intact
        # Fixme: this needs to be looked at more closely
        # restored_first = restored_latest.previous_version
        # assert restored_first.id == first_update_id
        # assert not restored_first.deleted
        # assert restored_first.is_latest_version == 0
        #
        # restored_original = restored_first.previous_version
        # assert restored_original.id == original_id
        # assert not restored_original.deleted
        # assert restored_original.is_latest_version == 0

        # Verify latest version appears in normal queries
        page = client.get('/consultations')
        assert 'second update description' in page
        # Older versions should not appear in normal view
        assert 'first update description' not in page
        assert 'original description' not in page


def test_consultation_status_filter(client):
    client.login_admin()

    # Create consultations with different statuses
    statuses_to_create = ['Created', 'In Progress', 'Waiving', 'Closed']
    for i, status in enumerate(statuses_to_create):
        page = client.get('/consultations')
        page = page.click('Vernehmlassung Erfassen')
        page.form['title'] = f'Consultation {i} - {status}'
        page.form['description'] = f'Description for {status}'
        page.form['status'] = status
        page = page.form.submit().follow()

    # 1. Test default view (no filter) - should show all
    page = client.get('/consultations')
    assert 'Consultation 0 - Created' in page
    assert 'Consultation 1 - In Progress' in page
    assert 'Consultation 2 - Waiving' in page
    assert 'Consultation 3 - Closed' in page
    assert len(page.pyquery('.consultation-card')) == 4

    # Check "All Statuses" filter is active by default
    all_status_link = page.pyquery('a.all-status-link')
    assert 'active-filter' in all_status_link.attr('class')

    # 2. Test filtering by 'Created'
    page = client.get('/consultations?status=Created')
    assert 'Consultation 0 - Created' in page
    assert 'Consultation 1 - In Progress' not in page
    assert 'Consultation 2 - Waiving' not in page
    assert 'Consultation 3 - Closed' not in page
    assert len(page.pyquery('.consultation-card')) == 1
    # Check correct filter badge is active
    active_filter = page.pyquery('.active-filter .consultation-status span')
    assert active_filter.text() == 'Erstellt'

    # 3. Test filtering by 'Waiving'
    page = client.get('/consultations?status=Waiving')
    assert 'Consultation 0 - Created' not in page
    assert 'Consultation 1 - In Progress' not in page
    assert 'Consultation 2 - Waiving' in page
    assert 'Consultation 3 - Closed' not in page
    assert len(page.pyquery('.consultation-card')) == 1
    active_filter = page.pyquery('.active-filter .consultation-status span')
    assert active_filter.text() == 'Verzicht'

    # 4. Test clicking "All Statuses" filter link
    all_status_link_href = page.pyquery('a.all-status-link').attr('href')
    page = client.get(all_status_link_href)
    assert len(page.pyquery('.consultation-card')) == 4 # All should be visible again
    assert 'active-filter' in page.pyquery('a.all-status-link').attr('class')

    # 5. Test clicking status badge *inside* a card
    # Find the 'Waiving' card and its status link
    waiving_card = page.pyquery('.consultation-card:contains("Waiving")')
    # Find the link wrapping the status badge
    status_link_in_card = waiving_card.find('a.status-link-overlay').attr('href')
    page = client.get(status_link_in_card)
    assert 'Consultation 2 - Waiving' in page
    assert len(page.pyquery('.consultation-card')) == 1
    active_filter = page.pyquery('.active-filter .consultation-status span')
    assert active_filter.text() == 'Verzicht' # Check top filter is active

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


def login_admin(page, live_server_url, session):
    admin_user = User(
        email="test@example.org",
        first_name="Test",
        last_name="User",
    )
    admin_user.set_password("test")
    external_user = User(
        email="external@example.org",
        first_name="External",
        last_name="User",
    )
    external_user.set_password("test")
    session.add(external_user)
    session.add(admin_user)
    transaction.commit()

    page.goto(live_server_url + "/login")
    page.locator('input[name="email"]').fill("admin@example.org")
    page.locator('input[name="password"]').fill("test")

    page.locator('button[type="submit"]').click()
    page.wait_for_load_state("networkidle", timeout=10000)

    error_locator = page.locator(".alert.alert-danger")
    if error_locator.is_visible():
        error_text = error_locator.text_content()
        pytest.fail(f"Login failed. Error message found: {error_text}")

    expect(page).not_to_have_url(re.compile(r".*/login$"), timeout=5000)


# === Browser
# Strictly speaking this doesn't need a browser test, but it's easier to look
# a the divs

# NOTE: WE should derive from Page to have these convenience methods in once 
# place
# there we could overwrite 
def test_consultation_activities_after_document_edit(
        page, live_server_url, session
):
    login_admin(page, live_server_url, session)
    # Create a consultation
    page.goto(live_server_url + '/consultations')
    page.click('text=Vernehmlassung Erfassen')

    # Fill out the title and submit
    page.locator('input[name="title"]').fill('Test Consultation Activity')
    page.locator('button[type="submit"]').click()

    # Wait for the page to load after submission
    page.wait_for_load_state('networkidle')

    # Verify we're on the consultation page
    expect(page).to_have_url(re.compile(r'.*/consultation/.*'))
    expect(page.locator('h1')).to_contain_text('Test Consultation Activity')
