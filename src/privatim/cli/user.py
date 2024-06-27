import click
from pyramid.paster import bootstrap
from pyramid.paster import get_appsettings
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from privatim.models import User
from privatim.orm import get_engine, Base
from sqlalchemy.orm import joinedload


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sqlalchemy.orm import Session


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

        user = User(email=email, first_name=first_name, last_name=last_name)
        user.set_password(password)
        dbsession.add(user)


def _delete_user(session: 'Session', email: str) -> bool:
    query = (
        select(User)
        .options(
            joinedload(User.leading_groups),
            joinedload(User.meetings),
            joinedload(User.statements),
            joinedload(User.comments),
            joinedload(User.consultations),
        )
        .filter(User.email == email)
    )

    existing_user = session.execute(query).unique().scalar_one_or_none()
    if not existing_user:
        click.echo(f"No user found with email {email}.")
        return False

    try:
        # # Remove user as leader from groups
        for group in existing_user.leading_groups:
            group.leader = None
        #
        # # Clear relationships
        # existing_user.groups = []
        # existing_user.meetings = []
        #
        # # Handle consultations
        # for consultation in existing_user.consultations:
        #     consultation.creator = None

        for comment in existing_user.comments:
            comment.user_id = None

        session.add(existing_user)
        session.flush()
        session.refresh(existing_user)
        session.delete(existing_user)
        session.flush()
        click.echo(f"User with email {email} successfully deleted.")
        return True
    except SQLAlchemyError as e:
        session.rollback()
        click.echo(
            f"Failed to delete user with email {email}. Error: {str(e)}"
        )
        return False


@click.command()
@click.argument('config_uri')
@click.option('--email', prompt=True)
def delete_user(config_uri: str, email: str) -> None:
    env = bootstrap(config_uri)
    settings = get_appsettings(config_uri)
    engine = get_engine(settings)
    Base.metadata.create_all(engine)

    with env['request'].tm:
        dbsession = env['request'].dbsession

        if _delete_user(dbsession, email):
            click.echo(
                f"User with email {email} has been deleted along with related "
                f"data."
            )
        else:
            click.echo(f"Failed to delete user with email {email}.")

        click.echo(
            f"User with email {email} has been deleted along with related "
            f"data."
        )
