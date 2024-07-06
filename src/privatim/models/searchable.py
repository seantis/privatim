from functools import wraps

from privatim.orm import Base


from typing import Iterator, TYPE_CHECKING
if TYPE_CHECKING:
    from sqlalchemy.orm import InstrumentedAttribute
    from privatim.types import HasSearchableFields


# todo(mypy) should this class implement the HasSearchableFields?
    #  Creates consequential errors...
class SearchableMixin:
    @classmethod
    def searchable_fields(cls) -> Iterator['InstrumentedAttribute[str]']:
        # Override this method in each model to specify searchable fields
        raise NotImplementedError(
            "Searchable fields must be defined for each model"
        )


def searchable_models() -> tuple[type['HasSearchableFields'], ...]:
    """Retrieve all models inheriting from SearchableMixin."""
    model_classes = set()
    for _ in Base.metadata.tables.values():
        for mapper in Base.registry.mappers:
            cls = mapper.class_
            if issubclass(cls, SearchableMixin):
                model_classes.add(cls)
    return tuple(model_classes)


def prioritize_search_field(f):
    """
    Mark as primary search fiel. This priorizites search matches for this
    column in `SearchCollection.build_attribute_query`.

    This decorator is used to annotate the `searchable_fields` method of a
    model (typically on it's title), indicating which field should be
    considered a more important field in search compared to other searchable
    fields.

    Usage:
        class YourModel(Base):

            @primary_search_field
            title: Mapped[str] = mapped_column(nullable=False)

            description: Mapped[str]

            def searchable_fields(self):
                yield 'title'
                yield 'description'

    Note:
        The decorated method ('searchable_fields') should yield
        all searchable fields, including the primary field. The primary
        field is weighted more in the search.
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        column = f(*args, **kwargs)
        column.is_primary_search_field = True
        return column
    return wrapper
