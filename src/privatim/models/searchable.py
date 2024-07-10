from functools import wraps

from privatim.orm import Base


from typing import Iterator, TYPE_CHECKING, TypeVar, Callable, Any

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
    def is_primary_search_field(
        cls: type[F], field: 'InstrumentedAttribute[Any]'
    ) -> bool:
        return field.key == _primary_search_fields.get(cls)

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


T = TypeVar('T')


def prioritize_search_field(
    primary_field: str,
) -> Callable[
    [Callable[[type[T]], Iterator['InstrumentedAttribute[Any]']]],
    Callable[[type[T]], Iterator['InstrumentedAttribute[Any]']],
]:
    """ Annotate the `searchable_fields` method of a model indicating which
    field should be considered a more important field in search compared to
    other searchable fields.

    For example:
        class YourModel(Base):

            title: Mapped[str] = mapped_column(nullable=False)

            description: Mapped[str]

            @prioritize_search_field('title)
            def searchable_fields(self):
                yield cls.title
                yield cls.description

    The search matches the title ranking higher in search.
    Note:
        The decorated method ('searchable_fields') should yield
        all searchable fields, including the primary field. The primary
        field is weighted more in the search.
    """

    def decorator(
        func: Callable[[type[T]], Iterator['InstrumentedAttribute[Any]']]
    ) -> Callable[[type[T]], Iterator['InstrumentedAttribute[Any]']]:
        @wraps(func)
        def wrapper(
            cls: type[T], *args: Any, **kwargs: Any
        ) -> Iterator['InstrumentedAttribute[Any]']:
            _primary_search_fields[cls] = primary_field
            return func(cls, *args, **kwargs)

        return wrapper

    return decorator
