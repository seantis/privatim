from sqlalchemy import func, update, Text
import transaction
from sqlalchemy.ext.hybrid import hybrid_property
import inspect
from sqlalchemy import text
import sys
from functools import cache

from sqlalchemy.orm import Session, class_mapper

from privatim.i18n import locales
from privatim.orm import Base


from typing import Iterator


class SearchableMixin:
    @classmethod
    def searchable_fields(cls) -> Iterator[str]:
        # Override this method in each model to specify searchable fields
        raise NotImplementedError(
            "Searchable fields must be defined for each model"
        )

    @hybrid_property
    def searchable_text(self) -> str:
        # todo: extract document text
        return ' '.join(
            str(getattr(self, field)) for field in self.searchable_fields()
        )


def searchable_models() -> tuple[type[Base], ...]:
    """Retrieve all models inheriting from SearchableMixin."""
    model_classes = set()
    for _ in Base.metadata.tables.values():
        for mapper in Base.registry.mappers:
            cls = mapper.class_
            if (
                inspect.isclass(cls)
                and issubclass(cls, SearchableMixin)
                and issubclass(cls, Base)
                and cls != SearchableMixin
            ):
                model_classes.add(cls)
    return tuple(model_classes)


def reindex_full_text_search(session: Session) -> None:
    """
    Updates the searchable_text_{} columns.

    1. We use func.cast() to explicitly cast the searchable_text_{locale}
    column to Text type.
    This ensures that we're passing a text value to to_tsvector,
    not a tsvector.
    j
    2. We wrap this in a func.coalesce() call, which will
    return an empty string if the column value is NULL. This prevents
    potential errors if some rows have NULL values in the searchable_text
    column.

    """
    models = searchable_models()
    # todo: remove later
    assert len(models) != 0, "No models with searchable fields found"
    for model in models:
        assert issubclass(model, SearchableMixin)
        for locale, language in locales.items():
            assert language == 'german'  # todo: remove later
            if hasattr(model, f'searchable_text_{locale}'):
                update_stmt = update(model).values(
                    {
                        f'searchable_text_{locale}': func.to_tsvector(
                            language, func.cast(model.searchable_text, Text)
                        )
                    }
                )
                updated = getattr(model, f'searchable_text_{locale}')
                session.execute(update_stmt)
                print(
                    'Reindex full text search for',
                    f'{model}.searchable_text_{locale} with val {updated}',
                )
    session.flush()
