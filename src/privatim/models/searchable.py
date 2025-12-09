from __future__ import annotations
from privatim.models.file import SearchableFile
from privatim.orm import Base


from typing import TYPE_CHECKING, TypeVar
from collections.abc import Iterator
if TYPE_CHECKING:
    from sqlalchemy.orm import InstrumentedAttribute
    from privatim.orm.meta import UUIDStrPK
    from sqlalchemy.orm import Mapped

F = TypeVar('F', bound='SearchableMixin')


class SearchableMixin:
    """ Enable full-text search in models inheriting from this class.
    The searchable_fields method must be implemented in each model to
    specify the fields to be searched. """

    if TYPE_CHECKING:
        id: Mapped[UUIDStrPK]

    @classmethod
    def searchable_fields(
        cls,
    ) -> Iterator[InstrumentedAttribute[str | None]]:
        raise NotImplementedError(
            "Searchable fields must be defined for each model"
        )


def searchable_models() -> tuple[type[SearchableMixin | SearchableFile], ...]:
    """Retrieve all models inheriting from SearchableMixin."""
    model_classes = set()
    for _ in Base.metadata.tables.values():
        for mapper in Base.registry.mappers:
            cls = mapper.class_
            if issubclass(cls, SearchableMixin) or issubclass(
                cls, SearchableFile
            ):
                model_classes.add(cls)
    return tuple(model_classes)


T = TypeVar('T')
