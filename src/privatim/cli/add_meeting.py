import argparse
import sys
from pyramid.paster import bootstrap
from pyramid.paster import get_appsettings
from pyramid.paster import setup_logging
from sedate import utcnow

from privatim.orm import get_engine
from privatim.models import User, Meeting, WorkingGroup
from privatim.orm import Base


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'config_uri',
        help='Configuration file, e.g., development.ini',
    )
    return parser.parse_args(argv[1:])


def main(argv: list[str] = sys.argv) -> None:
    """ Add some example placeholder content to the database."""

    args = parse_args(argv)
    setup_logging(args.config_uri)

    with bootstrap(args.config_uri) as env:
        settings = get_appsettings(args.config_uri)

        engine = get_engine(settings)
        Base.metadata.create_all(engine)

    with env['request'].tm:
        db = env['request'].dbsession
        add_example_content(db)


def add_example_content(db: 'Session') -> None:

    users = [
        User(
            email='foobar@example.org',
            password='test',  # nosec: B106
            first_name='thefirstname',
            last_name='thelastname',
        ),
    ]
    for user in users:
        user.set_password('test')
        try:
            db.add(user)
        except Exception as e:
            print(f'Error adding user: {e}')

    group1 = WorkingGroup(name='Arbeitsgruppe 1')
    for user in users:
        user.groups.append(group1)
    db.add(group1)
    db.flush()

    users = db.query(User).filter_by(email='foobar@example.org').all()
    meeting = Meeting(
        name='Die wöchentliche Sitzung',
        time=utcnow(),
        attendees=users,
        working_group=group1,
    )

    db.add_all([meeting])
    db.flush()


if __name__ == '__main__':
    main()
