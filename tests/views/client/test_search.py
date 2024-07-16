import logging
from webtest import Upload

from privatim.models import SearchableFile
from privatim.views.search import SearchCollection
from tests.shared.utils import create_consultation

logging.basicConfig(
    level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def test_search_client(client, pdf_vemz):

    # search in Files
    # search in Consultation [x]
    # search in Comments [ ]
    # search in AgendaItem [ ]

    client.login_admin()

    page = client.get('/consultations')

    page = page.click('Vernehmlassung Erfassen')
    page.form['title'] = 'test'
    page.form.submit()

    page = client.get('/consultations')
    page = page.click('Vernehmlassung Erfassen')
    page.form['title'] = 'test'
    page.form['description'] = 'the description'
    page.form['recommendation'] = 'the recommendation'
    page.form['evaluation_result'] = 'the evaluation result'
    page.form['decision'] = 'the decision'
    page.form['status'] = '1'
    page.form['secondary_tags'] = ['AG', 'ZH']
    page.form['files'] = Upload(*pdf_vemz)
    page = page.form.submit().follow()
    client.get('/')

    client.skip_n_forms = 0
    search_form = page.forms[0]
    search_form['term'] = 'Sehr geehrte Damen und Herren'
    page = search_form.submit().follow()
    headline = page.pyquery('div.search-result-headline')[0].text_content()
    assert ('Sehr geehrte Damen und Herren Wir danken Ihnen für die '
            'Gelegenheit, zum Vorentwurf') in headline


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
                    first_item)


def setup_search_scenario(pdf_to_search, session):
    documents = [SearchableFile(*pdf_to_search)]
    consultation = create_consultation(documents=documents)
    session.add(consultation)
    session.flush()
