from contextlib import contextmanager

from sqlalchemy import engine_from_config, event, Select
import zope.sqlalchemy
from sqlalchemy.orm import (
    sessionmaker,
    Session as BaseSession,
    with_loader_criteria,
)
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
    A custom SQLAlchemy Session class that adds WHERE criteria to all
    occurrences of an entity in all queries (GlobalFilter).

    Ignore models marked as 'deleted' in all queries, so developers don't have
    to remember this check every time they write a query. This is also done for
    Consultation versioning so we don't have to worry about accidentally
    fetching older versions of Consultations. In most cases, we only want the
    latest version.

    In the rare case where we actually do want the older versions, we can
    disable the filter as follows:

        with session.no_consultation_filter():
            all_consultations = session.query(Consultation).all()

    This has been found in the docs:
    https://docs.sqlalchemy.org/en/20/orm/session_events.html#adding-global-where-on-criteria  # noqa: E501
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._disable_consultation_filter = False

        @event.listens_for(self, "do_orm_execute")
        def _add_filtering_criteria(
                orm_execute_state: 'ORMExecuteState'
        ) -> None:
            if (
                orm_execute_state.is_select
                and not orm_execute_state.is_column_load
                and not orm_execute_state.is_relationship_load
                and not self._disable_consultation_filter
            ):
                from privatim.models.consultation import Consultation

                # Below, an option is added to all SELECT statements that
                # will limit all queries against Consultation to filter on
                # is_latest_version == True. The criteria will be applied to
                # all loads of that class within the scope of the immediate
                # query. The with_loader_criteria() option by default will
                # automatically propagate to relationship loaders as well (
                # lazy loads, selectinloads, etc.)
                orm_execute_state.statement = (
                    orm_execute_state.statement.options(
                        with_loader_criteria(
                            Consultation,
                            Consultation.is_latest_version == 1
                        )
                    )
                )

    @contextmanager
    def no_consultation_filter(self):  # type:ignore
        original_value = self._disable_consultation_filter
        self._disable_consultation_filter = True
        try:
            yield
        finally:
            self._disable_consultation_filter = original_value


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
