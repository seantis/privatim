import shutil
import tempfile
import pytest


@pytest.fixture(scope="function")
def temporary_directory():
    """ Provides a temporary directory that is removed after the test. """
    directory = tempfile.mkdtemp()
    yield directory
    shutil.rmtree(directory)
