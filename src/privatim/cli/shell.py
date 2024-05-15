from code import InteractiveConsole
import readline
import rlcompleter

import click
from pyramid.paster import bootstrap
from transaction import commit

from typing import Any

from privatim.cli.find_files import find_ini_file_or_abort


class EnhancedInteractiveConsole(InteractiveConsole):
    """Wraps the InteractiveConsole with some basic shell features:

    - horizontal movement (e.g. arrow keys)
    - history (e.g. up and down keys)
    - very basic tab completion
    """

    def __init__(self, locals: dict[str, Any] | None = None):
        super().__init__(locals)
        self.init_completer()

    def init_completer(self) -> None:
        readline.set_completer(
            rlcompleter.Completer(
                dict(self.locals) if self.locals else {}
            ).complete
        )
        readline.set_history_length(100)
        readline.parse_and_bind("tab: complete")


@click.command()
def shell() -> None:
    """Enters an interactive shell."""

    config_uri = find_ini_file_or_abort()
    assert 'development.ini' in config_uri

    env = bootstrap(config_uri)
    with env['request'].tm:
        session = env['request'].dbsession
        app = env['app']
        shell = EnhancedInteractiveConsole(
            {

                'app': app,
                'session': session,
                'commit': commit,
            }
        )
        shell.interact(
            banner="""
        privatim Shell
        ==================

        Exit the console using exit() or quit().

        Available variables: session
        Available functions: commit

        Example:
           from privatim.models.user import User
           query = session.query(User).filter_by(username='admin@example.org')
           user = query.one()
           user.username = 'info@example.org'
           commit()
           exit()
        """
        )
