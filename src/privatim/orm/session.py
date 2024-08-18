from contextlib import contextmanager
from sqlalchemy import event
from sqlalchemy.orm import Session as BaseSession, with_loader_criteria


from typing import Any, TYPE_CHECKING
if TYPE_CHECKING:
    from sqlalchemy.orm import ORMExecuteState


class FilteredSession(BaseSession):
    """
    Handles soft delete and versioning by wrapping the default SQLAlchemy
    Session.

    A custom SQLAlchemy Session class that adds WHERE criteria to all
    occurrences of an entity in all queries (GlobalFilter).

    Ignore models marked as 'deleted' in all queries, so developers don't have
    to remember this check every time they write a query. A similar thing  is
    also done for Consultation versioning so we don't have to worry about
    accidentally fetching older versions of Consultations. In most cases,
    we only want the latest version.

    In the rare case where we actually do want the older / deleted versions,
    we can disable the filter as follows:

        with session.no_consultation_filter():
            all_consultations = session.query(Consultation).all()

        or for soft deleted models:

        with session.no_soft_delete_filter():
            deleted_consultations = session.query(Consultation).filter(
                Consultation.deleted == True)


    This is the recommended way to handle this kind of global filtering.:
    https://docs.sqlalchemy.org/en/20/orm/session_events.html#adding-global-where-on-criteria  # noqa: E501
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._disable_consultation_filter = False
        self._disable_soft_delete_filter = False

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

                stmt = orm_execute_state.statement

                if not self._disable_consultation_filter:
                    stmt = stmt.options(
                        with_loader_criteria(
                            Consultation,
                            Consultation.is_latest_version == 1
                        )
                    )

                # Analogous to the above: soft delete.
                # Accumulate soft delete criteria for all models.
                from privatim.models.soft_delete import all_soft_delete_models
                if not self._disable_soft_delete_filter:
                    soft_delete_criteria = [
                        with_loader_criteria(
                            model,
                            model.deleted.is_(False)
                        )
                        for model in all_soft_delete_models()
                    ]
                    # Apply all criteria at once
                    stmt = stmt.options(*soft_delete_criteria)

                orm_execute_state.statement = stmt

    @contextmanager
    def no_consultation_filter(self):  # type:ignore
        original_value = self._disable_consultation_filter
        self._disable_consultation_filter = True
        try:
            yield
        finally:
            self._disable_consultation_filter = original_value

    @contextmanager
    def no_soft_delete_filter(self):  # type:ignore
        original_value = self._disable_soft_delete_filter
        self._disable_soft_delete_filter = True
        try:
            yield
        finally:
            self._disable_soft_delete_filter = original_value

    def delete(self, instance: Any, soft: bool = False) -> None:
        if soft and hasattr(instance, 'deleted'):
            instance.deleted = True
            self.add(instance)
            if hasattr(instance, 'cascade_soft_delete'):
                instance.cascade_soft_delete()
        else:
            super().delete(instance)
