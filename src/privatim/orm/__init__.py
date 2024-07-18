from contextlib import contextmanager

from sqlalchemy import engine_from_config, event, Select, Result
import zope.sqlalchemy
from sqlalchemy.orm import sessionmaker, Session as BaseSession
from .meta import Base


from typing import Any, TYPE_CHECKING
if TYPE_CHECKING:
    from sqlalchemy.engine import Engine
    from sqlalchemy.orm import ORMExecuteState


def get_engine(
        settings: dict[str, Any],
        prefix:   str = 'sqlalchemy.'
) -> 'Engine':

    return engine_from_config(
        settings,
        prefix,
        pool_pre_ping=True
    )


class FilteredSession(BaseSession):
    """
    A custom SQLAlchemy Session class that automatically filters Consultation
    queries. This session class applies a filter to all queries involving the
    Consultation model, ensuring that only records with is_latest_version == 1
    are returned by default.

    This is done so we don't have to worry about accidentally fetching older
    versions of Consultations. In most cases, we only want the latest version.

    In the rare case where we actually do want the older versions, we can
    disable the filter as follows:

        with session.no_consultation_filter():
            all_consultations = session.query(Consultation).all()
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._disable_consultation_filter = False

        @event.listens_for(self, "do_orm_execute")
        def _add_filtering_criteria(orm_execute_state: 'ORMExecuteState') -> None:
            if (
                orm_execute_state.is_select
                and not self._disable_consultation_filter
            ):
                orm_execute_state.statement = self._apply_consultation_filter(
                    orm_execute_state.statement
                )

    def _apply_consultation_filter(self, stmt: Any) -> Any:
        from privatim.models import Consultation
        if isinstance(stmt, Select):
            for ent in stmt.column_descriptions:
                if (entity := ent.get('entity')) is not None:
                    if entity is Consultation:
                        return stmt.filter(Consultation.is_latest_version == 1)
        return stmt

    @contextmanager
    def no_consultation_filter(self):  # type:ignore
        original_value = self._disable_consultation_filter
        self._disable_consultation_filter = True
        try:
            yield
        finally:
            self._disable_consultation_filter = original_value

    def execute(self, statement, *args, **kwargs):  # type:ignore
        if not self._disable_consultation_filter:
            statement = self._apply_consultation_filter(statement)
        return super().execute(statement, *args, **kwargs)

    def scalar(self, statement, *args: Any, **kwargs: Any) -> Any:  # type:ignore  # noqa
        if not self._disable_consultation_filter:
            statement = self._apply_consultation_filter(statement)
        return super().scalar(statement, *args, **kwargs)


def get_session_factory(engine: 'Engine') -> sessionmaker[FilteredSession]:
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
