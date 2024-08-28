# """
# Fixtures supporting end-to-end tests using Playwright.
#
# We start `potat` as a process in the background with a sqlite (in-memory)
# database. Both the server and database are initialized once at the start of the
# E2E tests and are destroyed after all tests ran. In pytest terms, the server
# fixture is session scoped.
#
# NOTE: The application state is not isolated per test, but global. That means,
# if you e.g., create a project in a test, this project will be present until the
# test session is done. Design your tests accordingly. That means running tests
# in parallel is not straightforward, although possible.
#
# The setup is based on this article:
# https://til.simonwillison.net/pytest/playwright-pytest
# """
# import json
# import os
# import subprocess
# import time
# from http.client import HTTPConnection
# from pathlib import Path
# from subprocess import PIPE
# from subprocess import Popen
#
# import pytest
# from playwright.sync_api import Browser
# from playwright.sync_api import StorageState
#
#
# from typing import TYPE_CHECKING
#
# from pytest_postgresql.config import get_config
# from pytest_postgresql.janitor import DatabaseJanitor
# import psycopg2
#
# from privatim import setup_filestorage
# from privatim.models import User
# from privatim.orm import Base, get_session_factory, get_engine
#
# if TYPE_CHECKING:
#     from sqlalchemy.orm import Session
#
# import pytest
# from pathlib import Path
# from pyramid.paster import get_appsettings
# from sqlalchemy import create_engine
# import subprocess
#
# # from https://github.com/pypi/warehouse/blob/5d15bfe/tests/conftest.py#L127
# @pytest.fixture(scope='session')
# def database(request):
#     config = get_config(request)
#     pg_host = config.get("host")
#     pg_port = config.get("port") or os.environ.get("PGPORT", 5432)
#     pg_user = config.get("user")
#     pg_db = config.get("db", "tests")
#     pg_version = config.get("version", 10.1)
#
#     janitor = DatabaseJanitor(pg_user, pg_host, pg_port, pg_db, pg_version)
#
#     # In case the database already exists, possibly due to an aborted test run,
#     # attempt to drop it before creating
#     janitor.drop()
#
#     # Create our Database.
#     janitor.init()
#     # Ensure our database gets deleted.
#     @request.addfinalizer
#     def drop_database():
#         janitor.drop()
#
#     return "postgresql://{}@{}:{}/{}".format(pg_user, pg_host, pg_port, pg_db)
#
#
# @pytest.fixture(scope='session')
# def seed_database(database, fixture_path: Path):
#     """ Initialize E2E test database using pytest-postgresql. """
#
#     config_uri = fixture_path / 'e2e.ini'
#
#     connection_string = database
#     breakpoint()
#
#     with open(config_uri, 'r') as f:
#         print(f.read())
#
#     if not config_uri.exists():
#         raise RuntimeError("Can not find e2e configuration!")
#
#     settings = get_appsettings(str(config_uri))
#     # overwrite (!)
#     settings['sqlalchemy.url'] = my_postgresql_proc.url()
#     engine = create_engine(my_postgresql_proc.url())
#     Base.metadata.drop_all(bind=engine)
#     setup_filestorage(settings)
#
#     # (Re-) create the test database
#     Base.metadata.create_all(bind=engine, checkfirst=True)
#
#     # initialize database and bootstrap catalogue data
#     subprocess.run(['upgrade', config_uri])
#
#     session_factory = get_session_factory(engine)
#     session = session_factory()
#
#     # Add testing user
#     e2e = User(email='e2e.test@seantis.ch', first_name='Foo', last_name='Bar')
#     e2e.set_password('e2e')
#     session.add(e2e)
#     session.commit()
#
#     yield session_factory
#
#     # Clean up
#     session.close()
#     Base.metadata.drop_all(bind=engine)
#
#
# @pytest.fixture
# def session(seed_database) -> 'Session':
#     """ Returns a session to the test database.  """
#     yield seed_database()
#
#
# @pytest.fixture(scope='session')
# def static_server(seed_database) -> None:
#     """ Start Pyramid app with pre-seeded database.  """
#     process = Popen(
#         ['pserve', 'tests/fixtures/e2e.ini'],
#         stdout=PIPE,
#         stderr=PIPE
#     )
#
#     retries = 5
#
#     while retries > 0:
#         conn = HTTPConnection('127.0.0.1:7654')
#         try:
#             conn.request('HEAD', '/')
#             response = conn.getresponse()
#             if response is not None:
#                 yield process
#                 break
#         except ConnectionRefusedError:
#             time.sleep(1)
#             retries -= 1
#
#     if not retries:
#         raise RuntimeError('Failed to start http server')
#     else:
#         process.terminate()
#         process.wait()
#
#
# @pytest.fixture(scope='session')
# def authenticated(static_server, browser: Browser) -> StorageState:
#     """
#     Authenticate test user and persist state, so the test suite does not have
#     to login before each test.
#
#     This setup is taken from the Playwright docs, see:
#     https://playwright.dev/python/docs/auth#reusing-signed-in-state
#     """
#     page = browser.new_page(locale='en-US')
#     page.set_viewport_size({'width': 1920, 'height': 1080})
#     page.goto('http://localhost:7654/login')
#
#     page.get_by_placeholder('Email address').fill('e2e.test@seantis.ch')
#     page.get_by_placeholder('Email address').press('Tab')
#     page.get_by_placeholder('Password').fill('e2e')
#     page.get_by_placeholder('Password').press('Enter')
#
#     return page.context.storage_state(path='state.json')
