import click
import transaction
from pyramid.paster import bootstrap
from pyramid.paster import get_appsettings
from privatim.models.searchable import reindex_full_text_search
from privatim.orm import get_engine, Base, get_session_factory, get_tm_session


@click.command()
@click.argument('config_uri')
def reindex(config_uri: str) -> None:

    bootstrap(config_uri)  # is this needed?
    settings = get_appsettings(config_uri)
    engine = get_engine(settings)
    Base.metadata.create_all(engine)

    session_factory = get_session_factory(engine)

    with transaction.manager:
        dbsession = get_tm_session(session_factory, transaction.manager)
        reindex_full_text_search(dbsession, transaction.manager)
