import logging

from sqlalchemy import func, Index
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, deferred, mapped_column, declared_attr
from sqlalchemy_utils import observes

from privatim.i18n import locales
from privatim.models.file import GeneralFile, SearchableFile
from privatim.models.utils import extract_pdf_info, word_count
from privatim.orm.associable import associated


from typing import ClassVar


logger = logging.getLogger(__name__)


class AssociatedFiles:
    """ Use this  mixin if uploaded files belong to a specific instance """

    # one-to-many
    files = associated(GeneralFile, 'files')


class SearchableAssociatedFiles:
    """ One-to-many files that belong to a specific instance that have their
        text contents extracted and stored in a single TSVECTOR column."""

    __name__: ClassVar[str]

    files: Mapped[list[SearchableFile]] = associated(
        SearchableFile, 'files'
    )

    @declared_attr
    def searchable_text_de_CH(cls) -> Mapped[TSVECTOR]:
        return deferred(mapped_column(
            TSVECTOR,
            nullable=True
        ))

    # fieme: Tricky typing
    @declared_attr
    def __table_args__(cls):  # type: ignore
        return (
            Index(
                f'idx_{cls.__tablename__.lower()}_searchable_text_de_CH',
                'searchable_text_de_CH',
                postgresql_using='gin'
            ),
        )

    def reindex_files(self) -> None:
        """Extract the text from the files and save it together with
        the language.
        """
        files_by_locale: dict[str, list[SearchableFile]] = {
            locale: [] for locale in locales
        }

        #  files are in 'de_CH' locale for now
        files_by_locale['de_CH'] = list(self.files)

        # Extract content and index
        for locale in locales:
            text = ''
            for file in files_by_locale[locale]:
                try:
                    pages, extract = extract_pdf_info(file.file)
                    file.extract = (extract or '').strip()
                    file.word_count = word_count(file.extract)
                    if file.extract:
                        text += '\n\n' + file.extract
                except Exception as e:
                    logger.error(f"Error processing file {file.id}: {str(e)}")

            setattr(
                self,
                f'searchable_text_{locale}',
                func.to_tsvector(locales[locale], text),
            )

    @observes('files')
    def files_observer(self) -> None:
        """
        Observer method for the 'files' relationship. Triggers a full reindex
        if any file changes.

        While potentially inefficient for large collections, it's typically
        fine as the number of files is expected to be small (1-5). Consider
        optimizing if performance issues arise.
        """

        self.reindex_files()
