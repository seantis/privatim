from privatim.orm import Base


from typing import Iterator, TYPE_CHECKING, TypeVar
if TYPE_CHECKING:
    from sqlalchemy.orm import InstrumentedAttribute
    from privatim.orm.meta import UUIDStrPK
    from sqlalchemy.orm import Mapped

F = TypeVar('F', bound='SearchableMixin')
_primary_search_fields: dict[type, str] = {}


class SearchableMixin:
    if TYPE_CHECKING:
        id: Mapped[UUIDStrPK]
    _primary_search_field: dict[type, str] = {}

    @classmethod
    def searchable_fields(
        cls,
    ) -> 'Iterator[InstrumentedAttribute[str | None]]':
        # Override this method in each model to specify searchable fields
        raise NotImplementedError(
            "Searchable fields must be defined for each model"
        )


def searchable_models() -> tuple[type[SearchableMixin], ...]:
    """Retrieve all models inheriting from SearchableMixin."""
    model_classes = set()
    for _ in Base.metadata.tables.values():
        for mapper in Base.registry.mappers:
            cls = mapper.class_
            if issubclass(cls, SearchableMixin):
                model_classes.add(cls)
    return tuple(model_classes)


T = TypeVar('T')
