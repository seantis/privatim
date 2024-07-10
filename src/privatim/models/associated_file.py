import logging
from io import BytesIO

from sqlalchemy import func, Index
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, declared_attr
from sqlalchemy_utils import observes  # type: ignore[import-untyped]

from privatim.i18n import locales
from privatim.models.file import GeneralFile, SearchableFile
from privatim.models.utils import extract_pdf_info, word_count
from privatim.orm.associable import associated


from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from privatim.orm.meta import UUIDStrPK


logger = logging.getLogger(__name__)


class AssociatedFiles:
    """ Use this mixin if uploaded files belong to a specific instance """

    files: Mapped[list[GeneralFile]] = associated(
        GeneralFile, 'files',
    )


class SearchableAssociatedFiles:
    """ Same as AssociatedFiles but provides the toolkit to make a list of
    files searchable, if they are pdfs. """

    if TYPE_CHECKING:
        id: Mapped[UUIDStrPK]
        __tablename__: Any

    files: Mapped[list[SearchableFile]] = associated(
        SearchableFile, 'files',
    )

    @declared_attr
    def searchable_text_de_CH(cls) -> Mapped[TSVECTOR]:
        return mapped_column(
            TSVECTOR,
            nullable=True
        )

    @declared_attr  # type: ignore[arg-type]
    def __table_args__(cls) -> tuple[Index, ...]:
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

        Note that for now only pdfs are supported.
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
                    pages, extract = extract_pdf_info(BytesIO(file.content))
                    file.extract = (extract or '').strip()
                    file.word_count = word_count(file.extract)
                    if file.extract:
                        text += '\n\n' + file.extract
                except Exception as e:
                    logger.error(f"Error extracting text contents for file"
                                 f" {file.id}: {str(e)}")

            setattr(
                self,
                f'searchable_text_{locale}',
                func.to_tsvector(locales[locale], text),
            )

    @observes('files')
    def files_observer(self) -> None:
        """
        Observer method for the 'files' relationship.
        While potentially inefficient for large collections, it's typically
        fine as the number of files is expected to be small (1-5). Consider
        optimizing if performance issues arise.
        """

        self.reindex_files()
