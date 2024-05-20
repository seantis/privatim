import warnings
import pytest
import sqlalchemy
import transaction
from libcloud.storage.drivers.local import LocalStorageDriver
from pyramid import testing
from sqlalchemy import engine_from_config
from privatim import main, setup_filestorage
from privatim.models import User, WorkingGroup
from privatim.models.consultation import Status, Consultation
from privatim.orm import Base, get_engine, get_session_factory, get_tm_session
from privatim.testing import DummyRequest, DummyMailer, MockRequests
from sqlalchemy_file.storage import StorageManager

from tests.shared.client import Client


@pytest.fixture
def base_config():
    msg = '.*SQLAlchemy must convert from floating point.*'
    warnings.filterwarnings('ignore', message=msg)

    config = testing.setUp(settings={
        'sqlalchemy.url': 'sqlite:///:memory:',
    })
    yield config
    testing.tearDown()
    transaction.abort()


@pytest.fixture
def config(base_config, monkeypatch, tmpdir):
    base_config.include('privatim.models')
    base_config.include('pyramid_chameleon')
    base_config.include('pyramid_layout')
    settings = base_config.get_settings()

    engine = get_engine(settings)
    # enable foreign key constraints in sqlite, so we can rely on them
    # working during testing.
    sqlalchemy.event.listen(
        engine,
        'connect',
        lambda c, r: c.execute('pragma foreign_keys=ON')
    )

    Base.metadata.create_all(engine)
    session_factory = get_session_factory(engine)

    dbsession = get_tm_session(session_factory, transaction.manager)
    base_config.dbsession = dbsession

    orig_init = DummyRequest.__init__

    def init_with_dbsession(self, *args, dbsession=dbsession, **kwargs):
        orig_init(self, *args, dbsession=dbsession, **kwargs)

    monkeypatch.setattr(DummyRequest, '__init__', init_with_dbsession)

    # Store static files in a temporary directory
    if not StorageManager._storages:
        # NOTE: StorageManager does not expose any method to check if some
        # storage has already been added. However, if you attempt to add a
        # storage that already exists, StorageManager raises a RuntimeError.
        tmpdir.mkdir('assets')
        container = LocalStorageDriver(tmpdir).get_container('assets')
        StorageManager.add_storage("default", container)

    return base_config


@pytest.fixture
def pg_config(postgresql, monkeypatch):
    config = testing.setUp(settings={
        'sqlalchemy.url': (
            f'postgresql+psycopg://{postgresql.info.user}:@'
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


@pytest.fixture
def session(config):
    # convenience fixture
    return config.dbsession


@pytest.fixture
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
def mailer(config):
    mailer = DummyMailer()
    config.registry.registerUtility(mailer)
    return mailer


@pytest.fixture()
def engine(app_settings):
    engine = engine_from_config(app_settings)
    Base.metadata.create_all(engine)

    # initialize file storage
    setup_filestorage(app_settings)

    return engine


@pytest.fixture
def connection(engine):
    connection = engine.connect()
    yield connection
    connection.close()


@pytest.fixture(scope="session")
def app_settings():
    yield {"sqlalchemy.url": "sqlite://"}


@pytest.fixture(scope="session")
def app_inner(app_settings):
    app = main({}, **app_settings)
    yield app


@pytest.fixture
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

    # Remove user, if not already done within a test.
    if user := client.db.get(User, user.id):
        client.db.delete(user)
        client.db.commit()

    client.reset()
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
