import logging
import os
from enum import Enum

import click
import plaster
import transaction
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, bindparam
from sqlalchemy.sql import text
from zope.sqlalchemy import mark_changed
from privatim.models import get_engine
from privatim.models import get_session_factory
from privatim.orm import Base


from typing import TYPE_CHECKING, Any, Optional, Literal, Union

if TYPE_CHECKING:
    from sqlalchemy import Column as _Column
    from sqlalchemy import Engine
    from sqlalchemy.orm import Session
    from sqlalchemy.engine.interfaces import ReflectedColumn

    Column = _Column[Any]

logger = logging.getLogger('privatim.upgrade')


class UpgradeContext:

    def __init__(self, db: 'Session'):
        self.session = db
        self.engine: Engine = self.session.bind  # type: ignore

        self.operations_connection = db._connection_for_bind(
            self.engine
        )
        self.operations: Operations = Operations(
            MigrationContext.configure(
                self.operations_connection
            )
        )
        # Default schema is 'public' for PostgreSQL
        self.schema = self.engine.url.query.get('schema', 'public')

    def has_table(self, table: str) -> bool:
        inspector = inspect(self.operations_connection)
        return table in inspector.get_table_names()

    def drop_table(self, table: str) -> bool:
        if self.has_table(table):
            self.operations.drop_table(table)
            return True
        return False

    def index_exists(self, table_name: str, index_name: str) -> bool:
        inspector = inspect(self.operations_connection)
        indexes = inspector.get_indexes(table_name)
        return any(index['name'] == index_name for index in indexes)

    def has_column(self, table: str, column: str) -> bool:
        inspector = inspect(self.operations_connection)
        return column in {c['name'] for c in inspector.get_columns(table)}

    def add_column(self, table:  str, column: 'Column') -> bool:
        if self.has_table(table):
            if not self.has_column(table, column.name):
                self.operations.add_column(table, column)
                return True
        return False

    def alter_column(
        self,
        table_name: str,
        column_name: str,
        *,
        nullable: Optional[bool] = None,
        comment: Union[str, Literal[False], None] = False,
        server_default: Any = False,
        new_column_name: Optional[str] = None,
        **kw: Any,
    ) -> bool:
        if not self.has_table(table_name):
            return False

        column_exists = self.has_column(table_name, column_name)
        new_column_exists = new_column_name and self.has_column(
            table_name, new_column_name
        )

        if not column_exists and not new_column_exists:
            return False

        if new_column_name and new_column_exists:
            return False

        # Proceed with alteration
        self.operations.alter_column(
            table_name,
            column_name,
            nullable=nullable,
            comment=comment,
            server_default=server_default,
            new_column_name=new_column_name,
            **kw,
        )
        return True

    def drop_column(self, table: str, name: str) -> bool:
        if self.has_table(table):
            if self.has_column(table, name):
                self.operations.drop_column(table, name)
                return True
        return False

    def has_foreign_key(self, table: str, constraint_name: str) -> bool:
        inspector = inspect(self.operations_connection)
        foreign_keys = inspector.get_foreign_keys(table)
        return any(fk['name'] == constraint_name for fk in foreign_keys)

    def create_foreign_key(
        self,
        constraint_name: Optional[str],
        source_table: str,
        referent_table: str,
        local_cols: list[str],
        remote_cols: list[str],
        *,
        onupdate: Optional[str] = None,
        ondelete: Optional[str] = None,
        deferrable: Optional[bool] = None,
        initially: Optional[str] = None,
        match: Optional[str] = None,
        source_schema: Optional[str] = None,
        referent_schema: Optional[str] = None,
        **dialect_kw: Any,
    ) -> bool:
        if self.has_table(source_table) and self.has_table(referent_table):
            self.operations.create_foreign_key(
                constraint_name,
                source_table,
                referent_table,
                local_cols,
                remote_cols,
                onupdate=onupdate,
                ondelete=ondelete,
                deferrable=deferrable,
                initially=initially,
                match=match,
                source_schema=source_schema,
                referent_schema=referent_schema,
                **dialect_kw
            )
            return True
        return False

    def get_column_info(
            self,
            table: str, column: str
    ) -> 'ReflectedColumn | None':
        """ Get type information about column. Use like this:

             col_info = context.get_column_info('consultations', column)
             if col_info and not isinstance(col_info['type'], MarkupText):
                do_something()
        """

        inspector = inspect(self.operations_connection)
        columns = inspector.get_columns(table)
        for col in columns:
            if col['name'] == column:
                return col
        return None

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

    def has_constraint(
        self, table_name: str, constraint_name: str, constraint_type: str
    ) -> bool:
        """ Check if a specific constraint exists on a table.

        When constraint names aren't known, they can be discovered:

        SELECT constraint_name FROM information_schema.table_constraints
        WHERE table_name = 'table_name'
        AND constraint_name LIKE '%column_name%';
        """
        # Ensure the connection is available
        conn = self.operations_connection
        if conn is None:
            logger.warning("Cannot check constraint, no connection available.")
            return False  # Or raise an error

        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE table_schema = :schema
                  AND table_name = :table_name
                  AND constraint_type = :constraint_type
                  AND constraint_name = :constraint_name
            )
        """).bindparams(
            bindparam('schema', value=self.schema),
            bindparam('table_name', value=table_name),
            bindparam('constraint_name', value=constraint_name),
            # Ensure type is upper case
            bindparam('constraint_type', value=constraint_type.upper()),
        )).scalar()
        return bool(result)  # Ensure boolean return

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
