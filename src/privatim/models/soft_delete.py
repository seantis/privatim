from functools import cache
from sqlalchemy import Boolean
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    object_session,
)
from privatim.orm import Base
from sqlalchemy.orm import declarative_mixin, Mapper, Session


from typing import TypeVar, TYPE_CHECKING
if TYPE_CHECKING:
    from sqlalchemy.orm import DeclarativeBase


T = TypeVar('T', bound='DeclarativeBase')


@declarative_mixin
class SoftDeleteMixin:
    deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    def _toggle_soft_delete(self, is_delete: bool) -> None:
        session: Session | None = object_session(self)
        if session is None:
            return

        self.deleted = is_delete

        mapper: Mapper = self.__class__.__mapper__  # type: ignore

        for rel in mapper.relationships:
            if 'delete' in rel.cascade:
                related_objects = getattr(self, rel.key)
                if isinstance(related_objects, list):
                    for related_obj in related_objects:
                        if isinstance(related_obj, SoftDeleteMixin):
                            related_obj.deleted = is_delete
                elif isinstance(related_objects, SoftDeleteMixin):
                    related_objects.deleted = is_delete

    def cascade_soft_delete(self) -> None:
        self._toggle_soft_delete(True)

    def revert_soft_delete(self) -> None:
        self._toggle_soft_delete(False)


@cache
def all_soft_delete_models() -> tuple[type[SoftDeleteMixin], ...]:
    """Retrieve all models inheriting from SoftDeleteMixin."""
    model_classes = set()
    for _ in Base.metadata.tables.values():
        for mapper in Base.registry.mappers:
            cls = mapper.class_
            if issubclass(cls, SoftDeleteMixin):
                model_classes.add(cls)
    return tuple(model_classes)
