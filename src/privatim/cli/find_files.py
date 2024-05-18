from typing import TYPE_CHECKING
import os
import click

if TYPE_CHECKING:
    from typing import Iterator


def find_ini_files(start_dir: str = '') -> 'Iterator[str]':
    start_dir = start_dir or os.path.dirname(os.path.abspath(__file__))
    visited = set()

    def recurse_directory(path: str) -> 'Iterator[str]':
        if path in visited:
            return
        visited.add(path)

        if os.path.isdir(path):
            try:
                with os.scandir(path) as entries:
                    for entry in entries:
                        if (
                            entry.is_file()
                            and entry.name.endswith('.ini')
                            and entry.name != 'testing.ini'
                        ):
                            yield entry.path
                        elif entry.is_dir():
                            yield from recurse_directory(entry.path)
            except PermissionError:
                print(f"Permission denied: {path}")

    current_path = start_dir

    yield from recurse_directory(current_path)

    for _ in range(10):  # limit the upward traversal to 10 levels
        parent_path = os.path.abspath(os.path.join(current_path, '..'))
        if parent_path in visited or parent_path == current_path:
            break
        yield from recurse_directory(parent_path)
        current_path = parent_path


def find_ini_file_or_abort() -> str:
    """  Automatically finds the development.ini or production.ini file.

    This function makes scripting easier by reducing the need to repeatedly
    specify the .ini file in the args for every command, encouraging its
    frequent use.

    It works by greedily searching file system from *here* upwards for .ini
    files. It then asks the user to confirm or quit.

    """
    for ini_file in find_ini_files():
        response = click.prompt(
            f'Found {ini_file} file. Use this file? (y/n/q)',
            type=str,
            default='n',
        )

        if response.lower() == 'y':
            click.echo('Continuing...')
            return ini_file
        elif response.lower() == 'q':
            click.echo('Quitting.')
            click.get_current_context().abort()
        else:
            click.echo('Searching for another file...')
            continue

    click.echo('No suitable .ini file found. Aborting.')
    click.get_current_context().abort()
