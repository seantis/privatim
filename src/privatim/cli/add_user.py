import click
from pyramid.paster import bootstrap
from pyramid.paster import get_appsettings

from privatim.models import User
from privatim.orm import get_engine, Base


@click.command()
@click.argument('config_uri')
@click.option('--email', prompt=True)
@click.option('--password', prompt=True, hide_input=True)
def add_user(config_uri: str, email: str, password: str) -> None:

    env = bootstrap(config_uri)
    settings = get_appsettings(config_uri)
    engine = get_engine(settings)
    Base.metadata.create_all(engine)

    with env['request'].tm:
        dbsession = env['request'].dbsession

        existing_user = dbsession.query(User).filter(User.email == email).first()
        if existing_user:
            click.echo(f"User with email {email} already exists.")
            return

        user = User(email=email)
        user.set_password(password)
        dbsession.add(user)
