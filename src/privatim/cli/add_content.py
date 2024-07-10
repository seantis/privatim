from pathlib import Path
from pyramid.paster import bootstrap, get_appsettings, setup_logging
from sqlalchemy import select, and_

from privatim.models.comment import Comment
from privatim.models.consultation import Status
from privatim.models.file import SearchableFile
from privatim.orm import get_engine
from privatim.models import (
    Consultation,
    User,
)
from privatim.orm import Base
import click


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


@click.command()
@click.argument('config_uri')
def main(config_uri: str) -> None:
    """Add some example placeholder content to the database."""
    setup_logging(config_uri)

    with bootstrap(config_uri) as env:
        settings = get_appsettings(config_uri)

        engine = get_engine(settings)
        Base.metadata.create_all(engine)

    with env['request'].tm:
        db = env['request'].dbsession
        add_content_mili(db)
        add_content_drittstaatsangehörigen(db)


def get_user(session: 'Session') -> User | None:
    """Very heuristically attempt to find the default user ."""
    stmt_ueli = select(User).filter(
        and_(User.first_name.contains('Ueli'), User.last_name.contains('Buri'))
    )
    user = session.scalars(stmt_ueli).first()
    return user


def add_content_drittstaatsangehörigen(db: 'Session') -> None:

    n = (
        'Übernahme und Umsetzung der Verordnung (EU) 2022/1190 zur Änderung '
        'der Verordnung (EU) 2018/1862 in Bezug auf die Eingabe von '
        'Informationsausschreibungen zu Drittstaatsangehörigen im Interesse '
        'der Union in das Schengener Informationssystem (SIS)'
    )
    consultation = (
        db.query(Consultation).filter(Consultation.title.ilike(n)).first()
    )

    ueli_buri = get_user(db)
    if ueli_buri is None:
        print("The user is required to initialize default data.")
        exit(1)

    if consultation:
        print(f'Already exists {n}')

    if not consultation:
        status = Status(name='Erstellt')
        print(f'Adding {n}')
        comments = [
            Comment(
                'Ich habe die Vorlage geprüft und beantrage den Verzicht auf '
                'eine Stellungnahme. Die geringe Tragweite der (im Rahmen '
                'des Schengen Acquis obligatorischen) Änderung wird '
                'ersichtlich, wenn die synoptische Tabelle zusammen mit der '
                'heutigen Fassung des BPI gelesen wird: - In Art. 15 Abs. 1 '
                'BPI kommt der neue Bst. kbis als zusätzlicher Zweck von '
                'RIPOL dazu; - in Art. 16 Abs. 2 BPI kommt der neue Bst. '
                'gbis als zusätzlicher Zweck von N-SIS dazu; - in Art. 16 '
                'Abs. 4 wird im Einleitungssatz geklärt, dass die dort '
                'genannten Stellen keine Ausschreibungen für die Eingabe in '
                'das N-SIS melden können, welche die neuen Inhalte betreffen '
                '(wie bisher für die Bst. a–g und h–r, aber nicht für den '
                'neuen gbis); die Vorschläge können hier nur von Europol '
                'kommen und werden von Fedpol geprüft (Abs. 4bis). Das '
                'erscheint mir alles als unproblematisch (und eben ohnehin '
                'zwingend). ',
                ueli_buri,
            ),
            Comment('Beschluss BA vom xx.yy.2024: Verzicht ', ueli_buri),
        ]
        consultation = Consultation(
            description='Die Europäische Union sieht mit der Verordnung (EU) '
            '2022/1190 vom 6. Juli 2022 vor, dass die Agentur '
            'der Europäischen Union für die Zusammenarbeit auf '
            'dem Gebiet der Strafverfolgung (Europol) im '
            'Schengener Informationssystem (SIS) zur Bekämpfung '
            'von schwerer Kriminalität und von Terrorismus '
            'Informationsausschreibungen bei Schengen Staaten '
            'veranlassen kann. Die Umsetzung ins Landesrecht '
            'erfordert eine Teilrevision des Bundesgesetzes über '
            'die polizeilichen Informationssysteme des Bundes ('
            'BPI). Mittels der Informationsausschreibungen ist '
            'für die Endnutzer des SIS, wie die Mitarbeitenden '
            'der Kantonspolizeien oder des Bundesamtes für Zoll '
            'und Grenzsicherheit (BAZG), bei einer Abfrage im '
            'SIS ersichtlich, dass eine bestimmte Person im '
            'Verdacht steht, in eine in den '
            'Zuständigkeitsbereich von Europol fallende Straftat '
            'verwickelt zu sein. Gestützt darauf ergreifen die '
            'zuständigen Behörden die in der Ausschreibung '
            'vorgesehenen Massnahmen. Weiter ist auch '
            'vorgesehen, dass Europol die Schweiz zur Eingabe '
            'von Informationsausschreibungen im SIS anfragen '
            'darf. Auch dies wird mit der geplanten '
            'landesrechtlichen Umsetzung ermöglicht. '
            'Vernehmlassungsfrist: 28. Juni 2024 ',
            recommendation='Vorschlag YJ: Stellungnahme Privatim, zumindest '
            'näher prüfen. Grund: Neben der Regelung des '
            'militärischen Gesundheitswesens im MG sollen '
            'auch beim Datenschutz - im Umgang mit '
            'medizinischen Informationen - Lücken in der '
            'Gesetzgebung geschlossen werden. Dazu sollen '
            'verschiedene Artikel des Bundesgesetzes über die '
            'militärischen Informationssysteme vom 3. Oktober '
            '200822 (MIG) angepasst werden. Dabei geht es '
            'darum, den Informationsaustausch zwischen den '
            'zuständigen Stellen des militärischen und des '
            'zivilen Gesundheitswesens zu regeln. Die neue '
            'Regelung wird es erlauben, Patientinnen und '
            'Patienten über die gesamte Behandlungskette im '
            'militärischen und zivilen Bereich durchgängig in '
            'gleich hoher Qualität zu beurteilen und zu '
            'betreuen. Stehen die Patientinnen und Patienten '
            'unter der Verantwortung des militärischen '
            'Gesundheitswesens, können medizinische '
            'Leistungen im militärischen wie auch im zivilen '
            'Gesundheitswesen aufgrund zeitgerechter '
            'gegenseitiger Information sicher erbracht '
            'werden. ',
            title=n,
            status=status,
            creator=ueli_buri,
        )
        db.add(consultation)
        db.add_all(comments)
        for comment in comments:
            consultation.comments.append(comment)

        db.add(status)
        db.flush()


def add_content_mili(db: 'Session') -> None:

    n = 'Änderung des Militärgesetzes und der Armeeorganisation'
    consultation = (
        db.query(Consultation).filter(Consultation.title == n).first()
    )

    ueli_buri = get_user(db)
    if ueli_buri is None:
        print("A user is required to initialize default data.")
        exit(1)

    if consultation:
        print(f'Already exists {n}')
    if not consultation:
        print(f'Adding {n}')
        status = Status(name='Erstellt')
        comments = [
            Comment(
                'Beschluss BA vom xx.yy.2020: ' 'Stellungnahme privatim',
                ueli_buri,
            ),
            Comment('Eingabe STN privatim am 23.12.2020.', ueli_buri),
        ]
        consultation = Consultation(
            title=n,
            description='Im Rahmen der Umsetzung zur Weiterentwicklung der '
            'Armee ist in der Praxis in einzelnen Bereichen '
            'Anpassungsbedarf erkannt worden. Davon betroffen '
            'sind insbesondere das Militärgesetz und die '
            'Armeeorganisation. Daneben besteht Handlungsbedarf '
            'bei der Sicherheit in der Militärluftfahrt und bei '
            'weiteren kleineren Regelungsbereichen in '
            'angrenzenden Rechtserlassen. Vernehmlassungsfrist: '
            '22. Januar 2021 ',
            recommendation='Vorschlag YJ vom 18.10.2020: Stellungnahme '
            'Privatim, zumindest näher prüfen. Grund: Neben '
            'der Regelung des militärischen Gesundheitswesens '
            'im MG sollen auch beim Datenschutz - im Umgang '
            'mit medizinischen Informationen - Lücken in der '
            'Gesetzgebung geschlossen werden. Dazu sollen '
            'verschiedene Artikel des Bundesgesetzes über die '
            'militärischen Informationssysteme vom 3. Oktober '
            '200822 (MIG) angepasst werden. Dabei geht es '
            'darum, den Informationsaustausch zwischen den '
            'zuständigen Stellen des militärischen und des '
            'zivilen Gesundheitswesens zu regeln. Die neue '
            'Regelung wird es erlauben, Patientinnen und '
            'Patienten über die gesamte Behandlungskette im '
            'militärischen und zivilen Bereich durchgängig in '
            'gleich hoher Qualität zu beurteilen und zu '
            'betreuen. Stehen die Patientinnen und Patienten '
            'unter der Verantwortung des militärischen '
            'Gesundheitswesens, können medizinische '
            'Leistungen im militärischen wie auch im zivilen '
            'Gesundheitswesen aufgrund zeitgerechter '
            'gegenseitiger Information sicher erbracht '
            'werden. ',
            status=status,
            creator=ueli_buri,
        )
        db.add(consultation)
        db.add_all(comments)
        for comment in comments:
            consultation.comments.append(comment)

        privatim_document_20201223 = get_file()
        consultation.files.append(privatim_document_20201223)
        db.add(status)
        db.add(privatim_document_20201223)
        db.flush()


def get_file() -> SearchableFile:
    here = Path(__file__).parent
    pdfname = '20201223_privatim_Vernehmlassung Änderung MG.pdf'
    pdf = here / 'sample-pdf-for-initialize-db' / pdfname
    return SearchableFile(pdfname, pdf.read_bytes())


if __name__ == '__main__':
    main()
