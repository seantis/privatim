from sqlalchemy import select
from sqlalchemy.orm import selectinload
from webtest import Upload
import transaction

from privatim.models import SearchableFile, Consultation
from privatim.models.meeting import AgendaItem
from privatim.views.search import SearchCollection
from tests.shared.utils import (
    create_consultation, hash_file, create_meeting_with_agenda_items
)


# ======= Client/View Integration Tests =======

def test_search_integration_flow(client, pdf_vemz, docx):
    """
    Tests the full search flow via the web client, including:
    - Searching for content within PDF and DOCX files attached to a Consultation.
    - Verifying highlighted search terms in results.
    - Checking file download links.
    - Adding multiple files to a consultation.
    """
    # search in Files [x]
    # search in Consultation [x]
    # search in AgendaItem [ ]

    client.login_admin()

    page = client.get('/consultations')

    page = page.click('Vernehmlassung Erfassen')
    page.form['title'] = 'test'
    page.form.submit()

    page = client.get('/consultations')
    page = page.click('Vernehmlassung Erfassen')
    page.form['title'] = 'The test title'
    page.form['description'] = 'the description'
    page.form['recommendation'] = 'the recommendation'
    page.form['evaluation_result'] = 'the evaluation result'
    page.form['decision'] = 'the decision'
    page.form['status'] = 'Created'
    page.form['secondary_tags'] = ['AG', 'ZH']
    pdf_name, pdf_bytes = pdf_vemz
    page.form['files'] = Upload(pdf_name, pdf_bytes)
    page = page.form.submit().follow()
    client.get('/')

    client.skip_n_forms = 0
    search_form = page.forms['search']
    search_form['term'] = 'Sehr geehrte Damen und Herren'
    page = search_form.submit().follow()
    file_search_result = page.pyquery(
        'div.search-result-headline'
    )[0].text_content()
    # test the section from file is displayed in headline
    assert (
        'Sehr geehrte Damen und Herren Wir danken Ihnen für die '
        'Gelegenheit, zum Vorentwurf'
    ) in file_search_result

    # test we have linked to the file
    file_link = page.pyquery('a.search-result-link')[0]
    response = client.get(file_link.get('href'))
    downloaded_file_bytes = response.body
    original_hash = hash_file(pdf_bytes)
    downloaded_hash = hash_file(downloaded_file_bytes)
    assert original_hash == downloaded_hash, 'File integrity check failed'

    consultation = client.db.scalars(
        select(Consultation)
        .where(Consultation.title == 'The test title')
        .options(selectinload(Consultation.files))
    ).first()

    page = client.get(f'/consultations/{consultation.id}/edit')
    assert 'Vernehmlassung bearbeiten' in page
    # page.form['file-1'] = Upload

    # Note: This kind of depends on implementation detail of the naming of
    # the id's of these fields.
    # radio boxes are:
    # keep = files-0-0
    # delete = files-0-1
    # replace = files-0-2
    # first upload field = files-0

    # "Upload additional files" field has the id 'files'
    # Let's upload the docx additionally to the pdf using the option
    # "Upload additional files" of UploadMultipleFilesWithORMSupport
    docx_name, docx_bytse = docx
    form = page.forms[1]
    form['files'] = Upload(docx_name, docx_bytse)
    page = form.submit().follow()

    search_form = page.forms['search']
    search_form['term'] = 'more text here'
    page = search_form.submit().follow()
    docx_search_result = page.pyquery(
        'div.search-result-headline'
    )[0].text_content()
    assert 'TEST' in docx_search_result
    assert 'more text here' in docx_search_result

    # Fetch the new consultation from the database
    new_consultation = client.db.scalars(
        select(Consultation)
        .where(Consultation.title == 'The test title')
        .options(selectinload(Consultation.files))
    ).first()


def test_search_agenda_item_integration(client):
    """ Tests searching for content within an AgendaItem. """
    client.login_admin()

    # Create a meeting with an agenda item
    # Rely on the test client's transaction management
    agenda_item_data = [{
        'title': 'Agenda Item Alpha',
        'description': 'Discussion about project Alpha progress.'
    }]
    meeting = create_meeting_with_agenda_items(
        agenda_items=agenda_item_data, session=client.db
    )
    # The helper function calls flush; check count directly on client.db
    assert client.db.query(AgendaItem).count() == 1

    # Go to a page with the search bar (e.g., dashboard)
    # Follow the redirect from '/'
    page = client.get('/').follow()

    # Perform search
    client.skip_n_forms = 0
    search_form = page.forms['search']
    search_form['term'] = 'Alpha'
    page = search_form.submit().follow()
    assert 'Es wurden keine Ergebnisse gefunden' not in page

    # Verify search result
    assert 'Agenda Item Alpha' in page
    assert 'Discussion about project Alpha progress.' in page
    search_results = page.pyquery('.card-body')
    assert len(search_results) == 1, "Expected one search result"

    # Verify the link points to the meeting
    details_link = search_results.find('a.details-link')
    assert details_link, "Details link not found"
    expected_url = f'/meetings/{meeting.id}'
    assert details_link.attr('href') == expected_url, \
        f"Link should point to {expected_url}"


def test_search_file_update_integration(client, pdf_vemz, pdf_new):
    """
    Tests searching after replacing a file in a Consultation.
    Ensures new content is found and old content is not.
    """
    client.login_admin()

    # 1. Create Consultation with initial PDF
    page = client.get('/consultations/new')
    page.form['title'] = 'Consultation with Updatable File'
    pdf_name_initial, pdf_bytes_initial = pdf_vemz
    # Unique content for initial PDF: "Sehr geehrte Damen und Herren"
    page.form['files'] = Upload(pdf_name_initial, pdf_bytes_initial)
    page = page.form.submit().follow()
    consultation_id = page.request.url.split('/')[-1] # Get ID from URL

    # 2. Search for initial content
    search_form = page.forms['search']
    search_form['term'] = 'Sehr geehrte Damen und Herren'
    search_page = search_form.submit().follow()
    assert 'Sehr geehrte Damen und Herren' in search_page, \
        "Initial PDF content not found after creation"
    assert len(search_page.pyquery('.search-result-link')) == 1, \
        "Expected one file result for initial PDF"

    # 3. Edit Consultation and replace the file
    page = client.get(f'/consultations/{consultation_id}/edit')
    form = page.forms[1] # Assuming the second form is for editing/files
    pdf_name_new, pdf_bytes_new = pdf_new
    # Unique content for new PDF: "This is the replacement document"
    form['files-0-action'] = 'replace' # Select 'replace' radio button
    form['files-0'] = Upload(pdf_name_new, pdf_bytes_new) # Upload new file
    page = form.submit().follow()

    # 4. Search for NEW content
    search_form = page.forms['search']
    search_form['term'] = 'replacement document'
    search_page_new = search_form.submit().follow()
    assert 'replacement document' in search_page_new, \
        "New PDF content not found after replacement"
    assert len(search_page_new.pyquery('.search-result-link')) == 1, \
        "Expected one file result for new PDF"

    # 5. Search for OLD content (should NOT be found)
    search_form = page.forms['search']
    search_form['term'] = 'Sehr geehrte Damen und Herren'
    search_page_old = search_form.submit().follow()
    assert 'Sehr geehrte Damen und Herren' not in search_page_old, \
        "Old PDF content should not be found after replacement"
    assert len(search_page_old.pyquery('.search-result-link')) == 0, \
        "Expected zero file results for old PDF content"


# ======= Test SearchCollection Directly =======

def test_search(session, pdf_vemz):
    # Create a consultation with an attached pdf:
    setup_search_scenario(pdf_vemz, session)

    query = 'grundsätzlichen Fragen:'
    collection: SearchCollection = SearchCollection(
        term=query, session=session
    )
    collection.do_search()

    for result in collection.results:
        if result.type == 'SearchableFile':
            first_item = next(iter(result.headlines.values()))
            assert ('grundsätzlichen</mark> <mark>Fragen</mark>:' in
                    first_item), 'Highlighting tags missing'


def setup_search_scenario(pdf_to_search, session):
    documents = [SearchableFile(*pdf_to_search)]
    consultation = create_consultation(documents=documents)
    session.add(consultation)
    session.flush()
