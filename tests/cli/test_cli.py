import os
from privatim.cli.find_files import find_ini_files
from tests.shared.fixtures import temporary_directory
from pathlib import Path


def find_src_directory(start_path: Path) -> Path:
    current_path = start_path.resolve()
    for parent in current_path.parents:
        if (parent / 'src').is_dir():
            return parent / 'src'
    raise FileNotFoundError('No src directory found')


def test_find_ini_files(temporary_directory):
    """
    Attempts to find the production.ini file upwards from the current
    """
    src = find_src_directory(Path(__file__))
    file__ = src / 'privatim' / 'cli' / 'find_files.py'
    assert file__.exists()
    file = next(find_ini_files(str(file__)))
    assert 'development.ini' in file

