from __future__ import annotations
from sqlalchemy import engine_from_config
import zope.sqlalchemy
from sqlalchemy.orm import sessionmaker
from .meta import Base
from privatim.orm.session import FilteredSession


from typing import Any, TYPE_CHECKING
if TYPE_CHECKING:
    from sqlalchemy.engine import Engine


def get_engine(
        settings: dict[str, Any],
        prefix:   str = 'sqlalchemy.'
) -> Engine:

    return engine_from_config(
        settings,
        prefix,
        pool_pre_ping=True
    )


def get_session_factory(engine: Engine) -> sessionmaker[FilteredSession]:
    factory = sessionmaker(class_=FilteredSession)
    factory.configure(bind=engine)
    return factory


def get_tm_session(
        session_factory: sessionmaker[FilteredSession],
        transaction_manager: Any
) -> FilteredSession:
    """
    Get a ``sqlalchemy.orm.Session`` instance backed by a transaction.

    This function will hook the session to the transaction manager which
    will take care of committing any changes.

    - When using pyramid_tm it will automatically be committed or aborted
      depending on whether an exception is raised.

    - When using scripts you should wrap the session in a manager yourself.
      For example:

          import transaction

          engine = get_engine(settings)
          session_factory = get_session_factory(engine)
          with transaction.manager:
              dbsession = get_tm_session(session_factory, transaction.manager)

    """
    dbsession = session_factory()
    zope.sqlalchemy.register(
        dbsession,
        transaction_manager=transaction_manager
    )
    return dbsession


__all__ = (
    'Base',
    'get_engine',
    'get_session_factory',
    'get_tm_session'
)
