from pathlib import Path
from pyramid.paster import bootstrap, get_appsettings, setup_logging
from privatim.models.consultation import Status, Tag
from privatim.orm import get_engine
from privatim.models import Consultation, ConsultationDocument
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
def main(config_uri: str, add_vemz: bool) -> None:
    """Add some example placeholder content to the database."""
    setup_logging(config_uri)

    with bootstrap(config_uri) as env:
        settings = get_appsettings(config_uri)

        engine = get_engine(settings)
        Base.metadata.create_all(engine)

    with env['request'].tm:
        db = env['request'].dbsession
        add_example_content(db, add_vemz)


def add_example_content(db: 'Session', add_vemz: bool) -> None:

    con_name = ('Vernehmlassung zur Interkantonalen Vereinbarung über den '
                'Datenaustausch zum Betrieb gemeinsamer Abfrageplattformen')
    consultation = (
        db.query(Consultation).filter(Consultation.title == con_name).first()
    )
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
        )
        db.add_all(tags)
        db.add(consultation)
        db.add(status)
        db.flush()

    if add_vemz:
        status = Status(name='In Überprüfung')
        tags = [Tag(name=n) for n in ['AG', 'ZH']]
        here = Path(__file__).parent
        pdfname = ('sample-pdf-for-initialize-db/privatim_Vernehmlassung_VEMZ'
                   '.pdf')
        pdf = here / pdfname
        content = pdf.read_bytes()
        consultation = Consultation(
            documents=[
                ConsultationDocument(
                    name=pdfname, content=content
                )
            ],
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


if __name__ == '__main__':
    main()
