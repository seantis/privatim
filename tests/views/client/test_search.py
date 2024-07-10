import pytest
from sqlalchemy import select
from sqlalchemy.orm import Mapped, mapped_column
from webtest import Upload
from psycopg import pq

from privatim.models import SearchableFile
from privatim.models.searchable import SearchableMixin
from privatim.models.searchable import prioritize_search_field
from privatim.orm import Base
from privatim.views.search import SearchCollection
from shared.utils import create_consultation


@pytest.fixture(scope='function')
def create_model(session):

    class MyModel(Base, SearchableMixin):
        __tablename__ = 'mymodel'

        id: Mapped[int] = mapped_column(primary_key=True)
        title: Mapped[str]

        description: Mapped[str]

        @classmethod
        @prioritize_search_field('title')
        def searchable_fields(cls):
            yield cls.title
            yield cls.description

    Base.metadata.create_all(session.bind)
    yield MyModel
    Base.metadata.drop_all(session.bind)


def test_model_definition(session, create_model):

    model = create_model(title='Test Title', description='Test Description')
    session.add(model)
    session.flush()  # Use flush instead of commit

    result = session.execute(
        select(create_model).filter_by(title='Test Title')
    ).scalar_one_or_none()
    assert result is not None
    assert result.description == 'Test Description'

    assert [
        'primary' if model.is_primary_search_field(field) else 'secondary'
        for field in model.searchable_fields()
    ] == ['primary', 'secondary']


def test_search(client, pdf_vemz, postgresql):

    cur = postgresql.cursor()
    res = cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    assert res.pgresult.status == pq.ExecStatus.COMMAND_OK
    res = cur.execute("CREATE EXTENSION IF NOT EXISTS btree_gin;")
    assert res.pgresult.status == pq.ExecStatus.COMMAND_OK

    postgresql.commit()
    cur.close()

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
    page.form['files'] = Upload(*pdf_vemz)
    page = page.form.submit().follow()

    client.skip_n_forms = 0
    # search for file content
    search_form = page.forms[0]
    search_form['term'] = 'Sehr geehrte Damen und Herren'
    search_result = search_form.submit().follow()


def test_search(session, pdf_vemz, postgresql):

    cur = postgresql.cursor()
    res = cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    assert res.pgresult.status == pq.ExecStatus.COMMAND_OK
    res = cur.execute("CREATE EXTENSION IF NOT EXISTS btree_gin;")
    assert res.pgresult.status == pq.ExecStatus.COMMAND_OK

    documents = [SearchableFile(*pdf_vemz)]
    consultation = create_consultation(documents=documents)
    session.add(consultation)

    query = 'grundsätzlichen Fragen:'

    collection: SearchCollection = SearchCollection(term=query, session=session)
    collection.do_search()
    return

    # search_results = []
    # for result in collection.results:
    #     if result.type == 'Comment':
    #         result.headlines['Content'] = Markup(  # noqa: MS001
    #             result.headlines['Content'])
    #
    #     if result.type in ['AgendaItem', 'Consultation', 'Meeting']:
    #         first_item = next(iter(result.headlines.items()))
    #         result.headlines['title'] = first_item[1]
    #
    #     search_results.append(result)
