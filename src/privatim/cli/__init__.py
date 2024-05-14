import os
import click
from privatim.cli.add_user import add_user
from privatim.utils import first


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Iterator


@click.group()
def cli() -> None:
    pass


cli.add_command(add_user)


def find_ini_files() -> 'Iterator[str]':
    current_path = os.path.dirname(os.path.abspath(__file__))
    while current_path != os.path.abspath(os.path.join(current_path, '..')):
        for filename in os.listdir(current_path):
            if filename.endswith('.ini'):
                yield os.path.join(current_path, filename)
        current_path = os.path.abspath(os.path.join(current_path, '..'))


def find_ini_file_or_abort() -> str:
    """ Search the file system from the current location for the
    development.ini or production.ini file

    Returns the absolute path to the .ini file """
    ini_file = first(find_ini_files())
    if click.confirm(f'Found {ini_file} file: continue? y/n'):
        click.echo('Continuing...')
        return ini_file
    else:
        click.echo('Stopping.')
        click.get_current_context().abort()


if __name__ == '__main__':
    cli()