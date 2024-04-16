import argparse
import sys

from pyramid.paster import bootstrap
from pyramid.paster import get_appsettings
from pyramid.paster import setup_logging

from privatim.orm import get_engine
from privatim.models import User
from privatim.models.group import WorkingGroup
from privatim.orm import Base


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'config_uri',
        help='Configuration file, e.g., development.ini',
    )
    return parser.parse_args(argv[1:])


def main(argv: list[str] = sys.argv) -> None:
    args = parse_args(argv)
    setup_logging(args.config_uri)

    with bootstrap(args.config_uri) as env:
        settings = get_appsettings(args.config_uri)

        engine = get_engine(settings)
        Base.metadata.create_all(engine)

        with env['request'].tm:
            db = env['request'].dbsession

            users = [
                User(email='admin@example.org', password='test',  # nosec:B110
                     first_name='Max', last_name='Müller'),
                User(email='user1@example.org', password='test',  # nosec:B110
                     first_name='Alexa', last_name='Troller'),
                User(email='user2@example.org', password='test',  # nosec:B110
                     first_name='Kurt', last_name='Huber')
            ]
            for user in users:
                user.set_password('test')
                db.add(user)

            group = WorkingGroup(
                name='Arbeitsgruppe 1'
            )
            for user in users:
                user.group = group
            db.add(group)
            db.flush()
