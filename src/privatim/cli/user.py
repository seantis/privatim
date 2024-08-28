import click
from pyramid.paster import bootstrap
from pyramid.paster import get_appsettings
from sqlalchemy import select

from privatim.models import User
from privatim.orm import get_engine, Base


@click.command()
@click.argument('config_uri')
@click.option('--email', prompt=True)
@click.option('--password', prompt=True, hide_input=True)
@click.option('--first_name')
@click.option('--last_name')
def add_user(
    config_uri: str, email: str, password: str, first_name: str, last_name: str
) -> None:

    env = bootstrap(config_uri)
    settings = get_appsettings(config_uri)
    engine = get_engine(settings)
    Base.metadata.create_all(engine)

    with env['request'].tm:
        dbsession = env['request'].dbsession

        query = select(User).filter(User.email == email)
        existing_user = dbsession.execute(query).scalar_one_or_none()
        if existing_user:
            click.echo(f"User with email {email} already exists.")
            return

        if not first_name or not last_name:
            click.echo("First name and last name are required.")
            return


        user = User(email=email, first_name=first_name, last_name=last_name)
        user.generate_profile_picture(dbsession)
        user.set_password(password)
        dbsession.add(user)
