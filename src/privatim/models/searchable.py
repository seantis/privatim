from privatim.orm import Base


from typing import Iterator, TYPE_CHECKING


if TYPE_CHECKING:
    from privatim.orm.meta import UUIDStrPK
    from sqlalchemy.orm import InstrumentedAttribute


class SearchableMixin:
    # if TYPE_CHECKING:
    #     id: UUIDStrPK

    @classmethod
    def searchable_fields(cls) -> Iterator['InstrumentedAttribute[str]']:
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
