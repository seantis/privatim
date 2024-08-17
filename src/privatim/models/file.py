import uuid
from io import BytesIO

from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy_file import File
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    deferred,
    relationship,
    declared_attr,
)

from privatim.models.soft_delete import SoftDeleteMixin
from privatim.models.utils import extract_pdf_info, word_count, get_docx_text
from privatim.orm.uuid_type import UUIDStr as UUIDStrType
from privatim.orm.abstract import AbstractFile
from sqlalchemy import Text, Integer, ForeignKey, Computed, Index


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from privatim.models import Consultation


class GeneralFile(AbstractFile):
    """A general file (image, document, pdf, etc), referenced in the database.

    A thin wrapper around the `File` from sqlalchemy-file so that we can easily
    route to the file via the usual pathway i.e. create_uuid_factory.

    """

    __tablename__ = 'general_files'

    __mapper_args__ = {
        'polymorphic_identity': 'general_file',
    }


class SearchableFile(AbstractFile, SoftDeleteMixin):
    """
    A file with the intention of being searchable.
    """

    __tablename__ = 'searchable_files'
    __mapper_args__ = {
        'polymorphic_identity': 'searchable_file',
    }

    consultation_id: Mapped[UUIDStrType] = mapped_column(
        ForeignKey('consultations.id', ondelete='CASCADE'), nullable=False
    )
    consultation: Mapped['Consultation'] = relationship(
        back_populates='files'
    )
    # the content of the given file as text.
    # (it is important that this column be loaded deferred by default, lest
    # we load massive amounts of text on simple queries)
    extract: Mapped[str | None] = deferred(mapped_column(Text, nullable=True))

    # The computed TSVECTOR column.
    # Note that this doesn't need a manual indexing by application code,
    # as "GENERATED ALWAYS AS" columns are automatically indexed.
    searchable_text_de_CH: Mapped[TSVECTOR] = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('german', COALESCE(extract, ''))",
            persisted=True,
        ),
        nullable=True
    )

    @declared_attr  # type:ignore[arg-type]
    def __table_args__(cls) -> tuple[Index, ...]:
        return (
            Index(
                f'idx_{cls.__tablename__.lower()}_searchable_text_de_CH',
                'searchable_text_de_CH',
                postgresql_using='gin'
            ),
            Index('ix_searchable_files_deleted', 'deleted'),
        )

    # these are supported for pdfs only for now.
    pages_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def __init__(
        self, filename: str, content: bytes, content_type: str | None = None
    ) -> None:
        self.id = str(uuid.uuid4())
        self.filename = filename

        if content_type is None:
            content_type = self.get_content_type(filename)

        if content_type == 'application/pdf':
            pages, extract = extract_pdf_info(BytesIO(content))
            self.extract = (extract or '').strip()
            self.pages_count = pages
            self.word_count = word_count(extract)
        elif content_type.startswith(
            'application/vnd.openxmlformats-officedocument.wordprocessingml'
        ):
            docx_text = get_docx_text(BytesIO(content))
            self.extract = (docx_text or '').strip()
        elif content_type == 'text/plain':
            self.extract = content.decode('utf-8').strip()
            self.pages_count = None  # Not applicable for text files
            self.word_count = word_count(content.decode('utf-8'))
        else:
            raise ValueError(f'Unsupported file type: {self.content_type}')

        self.file = File(
            content=content,
            filename=filename,
            content_type=content_type,
        )

    @staticmethod
    def get_content_type(filename: str) -> str:
        """
        Determine the content type based on the file extension.
        """
        extension = filename.lower().split('.')[-1]
        if extension == 'pdf':
            return 'application/pdf'
        elif extension in ['docx', 'doc', 'docm']:
            return ('application/vnd.openxmlformats-officedocument'
                    '.multiprocessing.document')
        elif extension == 'txt':
            return 'text/plain'
        else:
            raise ValueError(f'Unsupported file type: {extension}')
