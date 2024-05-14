import argparse
import logging
import os
from enum import Enum
from typing import TYPE_CHECKING
from typing import Any

import click
import plaster
import transaction
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect
from sqlalchemy.sql import text
from zope.sqlalchemy import mark_changed
from privatim.models import get_engine
from privatim.models import get_session_factory
from privatim.orm import Base


if TYPE_CHECKING:
    from sqlalchemy import Column as _Column
    from sqlalchemy import Engine
    from sqlalchemy.orm import Session

    Column = _Column[Any]

logger = logging.getLogger('privatim.upgrade')


class UpgradeContext:

    def __init__(self, db: 'Session'):
        self.session = db
        self.engine: 'Engine' = self.session.bind  # type: ignore

        self.operations_connection = db._connection_for_bind(
            self.engine
        )
        self.operations: Any = Operations(
            MigrationContext.configure(
                self.operations_connection
            )
        )

    def has_table(self, table: str) -> bool:
        inspector = inspect(self.operations_connection)
        return table in inspector.get_table_names()

    def drop_table(self, table: str) -> bool:
        if self.has_table(table):
            self.operations.drop_table(table)
            return True
        return False

    def has_column(self, table: str, column: str) -> bool:
        inspector = inspect(self.operations_connection)
        return column in {c['name'] for c in inspector.get_columns(table)}

    def add_column(self, table:  str, column: 'Column') -> bool:
        if self.has_table(table):
            if not self.has_column(table, column.name):
                self.operations.add_column(table, column)
                return True
        return False

    def drop_column(self, table: str, name: str) -> bool:
        if self.has_table(table):
            if self.has_column(table, name):
                self.operations.drop_column(table, name)
                return True
        return False

    def get_enum_values(self, enum_name: str) -> set[str]:
        if self.engine.name != 'postgresql':
            return set()

        # NOTE: This is very low-level but easier than using
        #       the sqlalchemy bind with a regular execute().
        result = self.operations_connection.execute(
            text("""
            SELECT pg_enum.enumlabel AS value
              FROM pg_enum
              JOIN pg_type
                ON pg_type.oid = pg_enum.enumtypid
             WHERE pg_type.typname = :enum_name
             GROUP BY pg_enum.enumlabel
            """),
            {'enum_name': enum_name}
        )
        return {value for (value,) in result}

    def update_enum_values(self, enum_type: type[Enum]) -> bool:
        # NOTE: This only adds new values, it doesn't remove
        #       old values. But the latter should probably
        #       not be a valid use case anyways.
        if self.engine.name != 'postgresql':
            return False

        assert issubclass(enum_type, Enum)
        # TODO: If we ever use a custom type name we need to
        #       be able to specify it. By default sqlalchemy
        #       uses the Enum type Name in lowercase.
        enum_name = enum_type.__name__.lower()
        existing = self.get_enum_values(enum_name)
        missing = {v.name for v in enum_type} - existing
        if not missing:
            return False

        # HACK: ALTER TYPE has to be run outside transaction
        self.operations.execute('COMMIT')
        for value in missing:
            # NOTE: This should be safe just by virtue of naming
            #       restrictions on classes and enum members
            self.operations.execute(
                f"ALTER TYPE {enum_name} ADD VALUE '{value}'"
            )
        # start a new transaction
        self.operations.execute('BEGIN')
        return True

    def commit(self) -> None:
        mark_changed(self.session)
        transaction.commit()


@click.command()
@click.argument('config_uri')
@click.option('--dry', is_flag=True, default=False)
def upgrade(config_uri: str, dry: bool) -> None:

    # Extract settings from INI config file.
    # We cannot use pyramid.paster.bootstrap() because loading the application
    # requires the proper DB structure.
    defaults = {'here': os.getcwd()}
    settings = plaster.get_settings(config_uri, 'app:main',
                                    defaults=defaults)

    # Setup DB.
    engine = get_engine(settings)
    Base.metadata.create_all(engine)
    session_factory = get_session_factory(engine)
    dbsession = session_factory()

    context = UpgradeContext(dbsession)
    module = __import__('privatim', fromlist='*')
    func = getattr(module, 'upgrade', None)
    if func is not None:
        print('Upgrading privatim')
        func(context)
    else:
        print('No pending upgrades')

    if not dry:
        context.commit()
