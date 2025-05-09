import click
from pyramid.paster import bootstrap
from pyramid.paster import get_appsettings
from sqlalchemy import select
from pyramid.request import Request

from privatim.models import Consultation
from privatim.orm import get_engine, Base

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from privatim.orm.session import FilteredSession


def print_consultation_tree(
    consultation: Consultation, level: int = 0
) -> None:
    """Print a single consultation and its version history recursively."""
    indent = '  ' * level
    version_status = 'LATEST' if consultation.is_latest() else 'OLD'
    click.echo(
        f'{indent}├── {consultation.title} ({version_status}) '
        f'[ID: {consultation.id}]'
    )

    if consultation.previous_version:
        print_consultation_tree(consultation.previous_version, level + 1)


def print_latest_consultations_with_files(
    dbsession: 'FilteredSession', request: Request
) -> None:
    """Print all latest consultations with their attached files."""
    query = select(Consultation).where(
        Consultation.is_latest_version == 1
    ).order_by(Consultation.title)

    latest_consultations = dbsession.execute(query).scalars().all()

    if not latest_consultations:
        click.echo('No latest consultations found.')
        return

    click.echo('\nLatest Consultations with Files:\n')

    for i, consultation in enumerate(latest_consultations, 1):
        url = request.route_url('consultation', id=consultation.id)
        click.echo(f'{i}. {consultation.title} [ID: {consultation.id}]')
        click.echo(f'   URL: {url}')
        click.echo(f'   Status: {consultation.status}')

        if consultation.files:
            for j, file in enumerate(consultation.files, 1):
                click.echo(f'   └── File {j}: {file.name}')
        else:
            click.echo('   └── No files attached')

        click.echo('')


@click.group()
def cli() -> None:
    """Consultation tree management commands."""
    pass


@cli.command('trees')
@click.argument('config_uri')
@click.option(
    '--title-filter',
    help='Only show consultations containing this text in the title',
)
@click.option(
    '--id',
    help='Print consultation tree by id',
)
def print_trees(
    config_uri: str,
    title_filter: str | None,
    id: str | None) -> None:
    """
    Print all consultation version trees.

    Shows the version history chains of all consultations, with optional title
    filtering.
    """
    env = bootstrap(config_uri)
    settings = get_appsettings(config_uri)
    engine = get_engine(settings)
    Base.metadata.create_all(engine)

    with env['request'].tm:
        dbsession = env['request'].dbsession

        with dbsession.no_consultation_filter():
            # Get all root consultations (those that are not previous versions)
            query = select(Consultation).where(
                Consultation.replaced_consultation_id.is_(None)
            )

            if title_filter:
                query = query.where(
                    Consultation.title.ilike(f'%{title_filter}%')
                )
            if id:
                breakpoint()
                query = query.where(Consultation.id == id)

            root_consultations = dbsession.execute(query).scalars().all()

            if not root_consultations:
                click.echo('No consultations found.')
                return

            click.echo('\nConsultation Version Trees:\n')

            # Sort by title for consistent output
            root_consultations.sort(key=lambda x: x.title)

            for i, consultation in enumerate(root_consultations, 1):
                click.echo(f'\nTree {i}:')
                print_consultation_tree(consultation)


@cli.command('latest-with-files')
@click.argument('config_uri')
def print_latest_with_files(config_uri: str) -> None:
    """
    Print all latest consultations with their attached files.

    Shows only the latest version of each consultation and lists their
    attached files.
    """
    env = bootstrap(config_uri)
    settings = get_appsettings(config_uri)
    registry = env['registry']
    engine = get_engine(settings)
    Base.metadata.create_all(engine)
    closer = env['closer']

    with env['request'].tm:
        dbsession = env['request'].dbsession

        # This is the crucial part, if we don't have this request_route url
        # will not respect the used path
        host = settings.get('pyramid.url_host', '127.0.0.1')
        port = settings.get('pyramid.url_port', '6543')
        scheme = settings.get('pyramid.url_scheme', 'http')
        http_host = f"{host}:{port}" if port and port != '80' else host
        server_port = str(port) if port else '80'
        environ = {
            'wsgi.url_scheme': scheme,
            'HTTP_HOST': http_host,
            'SERVER_NAME': host,
            'SERVER_PORT': server_port,
            # Add other minimal required environ keys if necessary
            'PATH_INFO': '/',
            'REQUEST_METHOD': 'GET',
        }

        request = Request(environ)
        # IMPORTANT: Associate the request with the application registry
        # This allows route_url to find the route definitions
        request.registry = registry

        print_latest_consultations_with_files(dbsession, request)
        closer()



def main() -> None:
    """Entry point for the console script."""
    cli()


if __name__ == '__main__':
    cli()
