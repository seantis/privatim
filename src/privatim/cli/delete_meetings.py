import argparse
import sys
from pyramid.paster import bootstrap
from pyramid.paster import get_appsettings
from pyramid.paster import setup_logging

from privatim.orm import get_engine
from privatim.models import Meeting
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
        delete_all_meetings(db)


def delete_all_meetings(db: 'Session') -> None:
    query = db.query(Meeting).all()
    for c in query:
        db.delete(c)
    db.commit()


if __name__ == '__main__':
    main()
