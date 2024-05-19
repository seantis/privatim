from code import InteractiveConsole
import readline
import rlcompleter
import transaction
import click
from pyramid.paster import bootstrap, get_appsettings

from privatim import setup_filestorage
from privatim.cli.find_files import find_ini_file_or_abort

from typing import Any

from privatim.orm import get_engine, get_session_factory, get_tm_session


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
    env = bootstrap(config_uri)
    settings = get_appsettings(config_uri)
    engine = get_engine(settings)
    session_factory = get_session_factory(engine)

    # prevent ObjectDoesNotExistError if querying a model with documents
    setup_filestorage(settings)

    with transaction.manager:
        dbsession = get_tm_session(session_factory, transaction.manager)
        app = env['app']
        shell = EnhancedInteractiveConsole(
            {
                'app': app,
                'session': dbsession,
                'commit': transaction.commit
            }
        )
        shell.interact(
            banner="""
        privatim Shell
        ==================

    Exit the console using exit() or quit().

    Available variables: session
    Available functions: commit

Example: Query User:
from privatim.models.user import User
query = session.query(User).filter_by(username='admin@example.org')
user = query.one()
user.username = 'info@example.org'
commit()
exit()

Example: Delete all Consultations:

from privatim.models import Consultation
query = session.query(Consultation).all()
[session.delete(c) for c in query];
commit()

"""
        )
