import logging
import warnings
import pytest
import transaction
from psycopg import pq
from pytest_postgresql import factories
from pyramid import testing
from pathlib import Path
from sqlalchemy import engine_from_config, text
from privatim import main
from privatim.file.setup import setup_filestorage
from privatim.models import User, WorkingGroup
from privatim.models.consultation import Status, Consultation
from privatim.orm import Base, get_engine, get_session_factory, get_tm_session
from privatim.testing import DummyRequest, DummyMailer, MockRequests
from tests.shared.client import Client


docker_config = {
    'host': 'localhost',  # or the IP of your Docker host
    'port': 5433,  # the port you mapped in your Docker run command
    'user': 'postgres',
    'password': 'password',
    'dbname': 'test_db'
}

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s')

postgresql_in_docker = factories.postgresql_noproc(**docker_config)
# it's important that this variable name is exactly 'postgresql'
# Because the name is shadowed
postgresql = factories.postgresql("postgresql_in_docker", load=[])
# requires pytest-postgresql:
@pytest.fixture(scope='function')
def pg_config(postgresql, monkeypatch):

    logger = logging.getLogger(__name__)
    logger.debug('Setting up pg_config fixture')

    config = testing.setUp(settings={
        'sqlalchemy.url': (
            f'postgresql+psycopg://{postgresql.info.user}:{postgresql.info.password}@'
            f'{postgresql.info.host}:{postgresql.info.port}'
            f'/{postgresql.info.dbname}'
        ),
    })
    config.include('privatim.models')
    config.include('pyramid_chameleon')
    config.include('pyramid_layout')
    settings = config.get_settings()

    engine = get_engine(settings)
    Base.metadata.create_all(engine)
    session_factory = get_session_factory(engine)

    dbsession = get_tm_session(session_factory, transaction.manager)
    config.dbsession = dbsession

    orig_init = DummyRequest.__init__

    def init_with_dbsession(self, *args, dbsession=dbsession, **kwargs):
        orig_init(self, *args, dbsession=dbsession, **kwargs)

    monkeypatch.setattr(DummyRequest, '__init__', init_with_dbsession)
    yield config
    try:
        transaction.commit()
    finally:
        # Make sure we always clean up regardless of whether or
        # not we can commit
        Base.metadata.drop_all(engine)
        testing.tearDown()
        transaction.abort()


@pytest.fixture(scope='function')
def session(pg_config):
    # convenience fixture
    return pg_config.dbsession


@pytest.fixture(scope='function')
def user(session):
    user = User(
        email='admin@example.org',
    )
    user.set_password('test')
    session.add(user)
    session.flush()
    session.refresh(user)
    return user


@pytest.fixture
def dummy_org(user):
    class DummyOrg:
        users = [user]

        def __iter__(self):
            yield user
    return DummyOrg


@pytest.fixture
def user_with_working_group(session):
    user = User(
        email='admin@example.org',
        first_name='John',
        last_name='Doe',
        groups=[WorkingGroup(name='Group')],
    )
    user.set_password('test')
    session.add(user)
    session.flush()
    session.refresh(user)
    return user


@pytest.fixture
def mailer(pg_config):
    mailer = DummyMailer()
    pg_config.registry.registerUtility(mailer)
    return mailer


@pytest.fixture(scope='function')
def engine(app_settings):
    engine = engine_from_config(app_settings)
    Base.metadata.create_all(engine)

    # initialize file storage
    setup_filestorage(app_settings)

    return engine


@pytest.fixture(scope='function')
def connection(engine):
    connection = engine.connect()
    yield connection
    connection.close()


@pytest.fixture(scope='function')
def app_settings(postgresql):
    yield {
        'sqlalchemy.url': (
            f'postgresql+psycopg://{postgresql.info.user}:{postgresql.info.password}@'
            f'{postgresql.info.host}:{postgresql.info.port}'
            f'/{postgresql.info.dbname}'
        ),
    }


@pytest.fixture(scope='function')
def app_inner(app_settings):
    app = main({}, **app_settings)
    yield app


@pytest.fixture(scope='function')
def app(app_inner, connection):
    app_inner.app.app.registry["dbsession_factory"].kw["bind"] = connection
    yield app_inner


@pytest.fixture(scope='function')
def client(app, engine):

    client = Client(app)
    client.db = get_session_factory(engine=engine)()

    user = User(email='admin@example.org')
    user.set_password('test')
    client.db.add(user)
    client.db.commit()

    yield client

    # Teardown
    client.db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def mock_requests(monkeypatch):
    monkeypatch.undo()
    mock_requests = MockRequests()
    monkeypatch.setattr(
        'requests.sessions.Session.request',
        mock_requests.mock_method
    )
    return mock_requests


@pytest.fixture()
def consultation(session) -> Consultation:
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
        recommendation=' Aus verfassungs- und datenschutzrechtlicher Sicht '
                       'ergeben sich einerseits grundsätzliche; Vorbehalte '
                       'und andererseits Hinweise zu einzelnen Bestimmungen '
                       'des Vereinbarungsentwurfs..',
        status=status,
    )
    session.add(consultation)
    session.add(status)
    session.flush()
    return consultation


@pytest.fixture()
def pdf_vemz():
    filename = 'search_test_privatim_Vernehmlassung_VEMZ.pdf'
    path = Path(__file__).parent / 'views/test_files' / filename
    with open(path, 'rb') as f:
        yield filename, f.read()
