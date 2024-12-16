import click
from pyramid.paster import bootstrap
from pyramid.paster import get_appsettings
from sqlalchemy import select

from privatim.models import Consultation
from privatim.orm import get_engine, Base


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


@click.command()
@click.argument('config_uri')
@click.option(
    '--title-filter',
    help='Only show consultations containing this text in the title',
)
def main(config_uri: str, title_filter: str | None) -> None:
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

        # We need to disable consultation filter to see all versions
        with dbsession.no_consultation_filter():
            # Get all root consultations (those that are not previous versions)
            query = select(Consultation).where(
                Consultation.replaced_consultation_id.is_(None)
            )

            if title_filter:
                query = query.where(
                    Consultation.title.ilike(f'%{title_filter}%')
                )

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


if __name__ == '__main__':
    main()
