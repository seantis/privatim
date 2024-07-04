import click
from pyramid.paster import bootstrap
from sqlalchemy import select, func

from privatim.models import SearchableAssociatedFiles
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
            if issubclass(cls, SearchableAssociatedFiles) and cls not in seen:
                seen.add(cls)
                click.echo(f"\nProcessing model: {cls.__name__}")
                stmt = select(cls.searchable_text_de_CH)
                results = db.execute(stmt).fetchall()
                for id, tsvector in results:
                    click.echo(f"ID: {id}")
                    click.echo(f"TSVector: {tsvector}")
                    click.echo("---")


@click.command()
@click.argument('config_uri')
def print_text(config_uri: str) -> None:
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
            if issubclass(cls, SearchableAssociatedFiles) and cls not in seen:
                seen.add(cls)
                click.echo(f"\nProcessing model: {cls.__name__}")
                texts2 = db.execute(select(
                    func.string_agg(SearchableFile.extract, ' ')).select_from(
                    cls).join(cls.files).group_by(cls.id)).all()
                for content in texts2:
                    click.echo(f"text_contents: {content}")
                    click.echo("---")


@click.command()
@click.argument('config_uri')
def reindex(config_uri: str) -> None:

    env = bootstrap(config_uri)

    with env['request'].tm:
        db = env['request'].dbsession
        seen = set()
        for mapper in Base.registry.mappers:
            cls = mapper.class_
            if issubclass(cls, SearchableAssociatedFiles) and cls not in seen:
                seen.add(cls)
                click.echo(f"\nProcessing model: {cls.__name__}")

                stmt = select(cls)
                results = db.execute(stmt).scalars().fetchall()
                for instance in results:
                    assert isinstance(instance, cls)
                    name = getattr(instance, 'title', None)
                    if name is not None:
                        click.echo(f"\nReindexing model: {cls.__name__} with "
                                   f"title: {name[:30]}")
                    else:
                        click.echo(f"\nReindexing model: {cls.__name__} with")

                    instance.reindex_files()
