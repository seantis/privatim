import click
from privatim.cli.add_user import add_user


@click.group()
def cli() -> None:
    pass


cli.add_command(add_user)


if __name__ == '__main__':
    cli()