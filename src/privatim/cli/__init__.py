import click

from .add_user import add_user


@click.group()
def cli() -> None:
    pass


cli.add_command(add_user)
