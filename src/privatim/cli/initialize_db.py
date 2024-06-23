from datetime import datetime
from functools import cache
from pathlib import Path
from pyramid.paster import bootstrap, get_appsettings, setup_logging
from sqlalchemy import select

from privatim.layouts.layout import DEFAULT_TIMEZONE
from privatim.models.consultation import Status, Tag
from privatim.orm import get_engine
from privatim.models import (Consultation, User, Meeting, WorkingGroup,
                             AgendaItem, GeneralFile)
from privatim.orm import Base
import click


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sqlalchemy.orm import Session


@click.command()
@click.argument('config_uri')
@click.option(
    '--add-vemz',
    is_flag=True,
    help='Add Verordnung über den Einsatz elektronischer Mittel',
)
@click.option(
    '--add-meeting',
    is_flag=True,
    help='Add a meeting with AgendaItem',
)
def main(config_uri: str, add_vemz: bool, add_meeting: bool) -> None:
    """Add some example placeholder content to the database."""
    setup_logging(config_uri)

    with bootstrap(config_uri) as env:
        settings = get_appsettings(config_uri)

        engine = get_engine(settings)
        Base.metadata.create_all(engine)

    with env['request'].tm:
        db = env['request'].dbsession
        add_example_content(db, add_vemz, add_meeting)


@cache
def get_first_admin_user(session: 'Session') -> User | None:
    stmt = select(User).filter(User.email.contains('admin'))
    return session.scalars(stmt).first()


def add_example_content(
    db: 'Session', add_vemz: bool, add_meeting: bool
) -> None:

    con_name = (
        'Vernehmlassung zur Interkantonalen Vereinbarung über den '
        'Datenaustausch zum Betrieb gemeinsamer Abfrageplattformen'
    )
    consultation = (
        db.query(Consultation).filter(Consultation.title == con_name).first()
    )

    admin_user = get_first_admin_user(db)
    if admin_user is None:
        print("A user 'admin' is required to initialize default data.")
        exit(1)

    if not consultation:
        status = Status(name='In Bearbeitung')
        tags = [Tag(name=n) for n in ['BS', 'BE', 'AI']]
        consultation = Consultation(
            title=con_name,
            description='Stellungnahme von privatim, Konferenz der '
            'schweizerischen Datenschutzbeauftragten, zum Entwurf '
            'einer Interkantonalen Vereinbarung über den '
            'Datenaustausch zum Betrieb gemeinsamer '
            'Abfrageplattformen, zu welcher die Konferenz der '
            'Kantonalen Justiz- und Polizeidirektorinnen und '
            '–direktoren (KKJPD) zur Zeit eine Vernehmlassung '
            'durchführt.',
            recommendation='Stellungnahme privatim näher prüfen.',
            status=status,
            secondary_tags=tags,
            creator=admin_user,
        )
        db.add_all(tags)
        db.add(consultation)
        db.add(status)
        db.flush()

    if add_vemz:
        status = Status(name='In Überprüfung')
        tags = [Tag(name=n) for n in ['AG', 'ZH']]
        here = Path(__file__).parent
        pdfname = 'privatim_Vernehmlassung_VEMZ.pdf'
        pdf = here / 'sample-pdf-for-initialize-db/' / pdfname
        content = pdf.read_bytes()
        consultation = Consultation(
            documents=[GeneralFile(filename=pdfname, content=content)],
            title='Verordnung über den Einsatz elektronischer Mittel zur Ton- '
            'und Bildübertragung in Zivilverfahren (VEMZ)',
            description='Mit der Revision der Schweizerischen '
            'Zivilprozessordnung können die Gerichte in '
            'Zivilverfahren ab dem 1. Januar 2025 unter bestimmten '
            'Voraussetzungen mündliche Prozesshandlungen (insb. '
            'Verhandlungen) mittels Video- und ausnahmsweise mittels '
            'Telefonkonferenzen durchführen oder den am Verfahren '
            'beteiligten Personen die Teilnahme mittels solcher '
            'Mittel gestatten. In der neuen Verordnung regelt der '
            'Bundesrat die technischen Voraussetzungen und die '
            'Anforderungen an den Datenschutz und die '
            'Datensicherheit beim Einsatz dieser Mittel. So sollen '
            'die Gerichte und Verfahrensbeteiligten über die '
            'notwendige Infrastruktur verfügen und beim Einsatz '
            'gewisse Vorgaben einhalten. Durch ausreichende '
            'Schutzvorkehrungen und Information der Teilnehmenden '
            'soll gewährleistet werden, dass die Daten aller '
            'Beteiligten bei der Vorbereitung und Durchführung der '
            'Prozesshandlung sowie bei der Aufzeichnung von Ton und '
            'Bild hinreichend geschützt sind. Vernehmlassungsfrist: '
            '22. Mai 2024 ',
            recommendation='Stellungnahme privatim näher prüfen.',
            status=status,
            secondary_tags=tags,
        )
        db.add_all(tags)
        db.add(consultation)
        db.add(status)
        db.flush()

    if add_meeting:
        attendees = [admin_user]
        agenda_items = [
            AgendaItem(
                title='Begrüssung',
                description='Begrüssung der Anwesenden und Eröffnung der '
                'Sitzung',
            ),
            AgendaItem(
                title='Neque porro quisquam est qui dolorem',
                description='Lorem ipsum dolor sit amet, consectetur '
                            'adipiscing elit. Nulla dui metus, viverra '
                            'tristique congue eu, congue sit amet mauris. In '
                            'ornare metus ut tellus auctor aliquet. In mi '
                            'leo, convallis rhoncus ipsum a, convallis '
                            'rutrum leo. Ut iaculis lacinia dolor id '
                            'convallis. Class aptent taciti sociosqu ad '
                            'litora torquent per conubia nostra, '
                            'per inceptos himenaeos. ',
            ),
        ]
        meeting = Meeting(
            name='Cras Tristisque',
            time=datetime.now(tz=DEFAULT_TIMEZONE),
            attendees=attendees,
            working_group=WorkingGroup(
                name='1. Gremium', leader=admin_user, users=attendees
            ),
            agenda_items=agenda_items
        )
        db.add_all(agenda_items)
        db.add(meeting)
        db.flush()


if __name__ == '__main__':
    main()
