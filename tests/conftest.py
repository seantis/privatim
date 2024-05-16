import warnings
import pytest
import sqlalchemy
import transaction
from pyramid import testing
from sedate import utcnow
from sqlalchemy import engine_from_config
from privatim import main
from privatim.models import User, WorkingGroup
from privatim.models.consultation import Status, Consultation
from privatim.orm import Base, get_engine, get_session_factory, get_tm_session
from privatim.testing import DummyRequest
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
def config(base_config, monkeypatch):
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
        first_name='John',
        last_name='Doe',
        password='test',
        created=utcnow(),
    )
    session.add(user)
    session.flush()
    session.refresh(user)
    return user


@pytest.fixture
def user_with_working_group(session):
    user = User(
        email='admin@example.org',
        first_name='John',
        last_name='Doe',
        password='test',
        created=utcnow(),
        groups=[WorkingGroup(name='Group')],
    )
    session.add(user)
    session.flush()
    session.refresh(user)
    return user


@pytest.fixture()
def engine(app_settings):
    engine = engine_from_config(app_settings)
    Base.metadata.create_all(engine)
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
