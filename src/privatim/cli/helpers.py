import click
from pyramid.paster import bootstrap
from sqlalchemy import select

from privatim.models.file import SearchableFile
from privatim.orm import Base


@click.command()
@click.argument('config_uri')
def print_tsvectors(config_uri: str) -> None:
    """
    Iterate over all models inheriting from SearchableAssociatedFiles
    and print their tsvector of searchable_text.
    """
    env = bootstrap(config_uri)

    with env['request'].tm:
        db = env['request'].dbsession
        seen = set()
        for mapper in Base.registry.mappers:
            cls = mapper.class_
            if issubclass(cls, SearchableFile) and cls not in seen:
                seen.add(cls)
                click.echo(f"\nProcessing model: {cls.__name__}")
                stmt = select(cls.searchable_text_de_CH)
                results = db.execute(stmt).fetchall()
                for id, tsvector in results:
                    click.echo(f"ID: {id}")
                    click.echo(f"TSVector: {tsvector}")
                    click.echo("---")
