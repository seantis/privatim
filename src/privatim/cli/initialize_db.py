from pyramid.paster import bootstrap, get_appsettings, setup_logging
from sqlalchemy.exc import IntegrityError
from privatim.models.consultation import Status
from privatim.orm import get_engine
from privatim.models import User, Consultation
from privatim.models.group import WorkingGroup
from privatim.orm import Base
import click
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


@click.command()
@click.argument('config_uri')
@click.option(
    '--only-consultation',
    is_flag=True,
    help='Add only a consultation without users',
)
def main(config_uri: str, only_consultation: bool) -> None:
    """Add some example placeholder content to the database."""
    setup_logging(config_uri)

    with bootstrap(config_uri) as env:
        settings = get_appsettings(config_uri)

        engine = get_engine(settings)
        Base.metadata.create_all(engine)

    with env['request'].tm:
        db = env['request'].dbsession
        add_example_content(db, only_consultation)


def add_example_content(db: 'Session', only_consultation: bool) -> None:
    if not only_consultation:
        users = [
            User(
                email='admin2@example.org',
                first_name='Max',
                last_name='Müller',
            ),
            User(
                email='user1@example.org',
                first_name='Alexa',
                last_name='Troller',
            ),
            User(
                email='user2@example.org',
                first_name='Kurt',
                last_name='Huber',
            ),
        ]
        print(f'Adding users: {users}')
        for user in users:
            user.set_password('test')
            try:
                db.add(user)
                db.flush()
            except IntegrityError as e:
                print(f'Error adding user: {e}')
                return

        group1 = WorkingGroup(name='Arbeitsgruppe 1')
        group2 = WorkingGroup(name='Arbeitsgruppe 2')
        for user in users:
            user.groups.append(group1)
        for user in users[:2]:
            user.groups.append(group2)
        db.add_all([group1, group2])

    # add a consultations:
    status = Status(name='In Bearbeitung')
    consultation = Consultation(
        title='Vernehmlassung zur Interkantonalen Vereinbarung über den '
        'Datenaustausch zum Betrieb gemeinsamer Abfrageplattformen  ',
        description='Stellungnahme von privatim, Konferenz der '
        'schweizerischen Datenschutzbeauftragten, zum Entwurf '
        'einer Interkantonalen Vereinbarung über den '
        'Datenaustausch zum Betrieb gemeinsamer '
        'Abfrageplattformen, zu welcher die Konferenz der '
        'Kantonalen Justiz- und Polizeidirektorinnen und '
        '–direktoren (KKJPD) zur Zeit eine Vernehmlassung '
        'durchführt.',
        recommendation=' Aus verfassungs- und datenschutzrechtlicher Sicht '
        'ergeben sich einerseits grundsätzliche; Vorbehalte '
        'und andererseits Hinweise zu einzelnen Bestimmungen '
        'des Vereinbarungsentwurfs..',
        status=status,
    )
    db.add(consultation)
    db.add(status)
    db.flush()


if __name__ == '__main__':
    main()
