import uuid
from io import BytesIO
import logging

import magic
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy_file import File
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    deferred,
    relationship,
    declared_attr,
)

from privatim.forms.validators import word_mimetypes, DEFAULT_DOCX_MIME
from privatim.models.soft_delete import SoftDeleteMixin
from privatim.models.utils import extract_pdf_info, word_count, get_docx_text
from privatim.orm.uuid_type import UUIDStr as UUIDStrType
from privatim.orm.abstract import AbstractFile
from sqlalchemy import (
    Text, Integer, ForeignKey, Computed, Index, CheckConstraint
)


logger = logging.getLogger('privatim.models.file')


from typing import TYPE_CHECKING  # noqa:E402
if TYPE_CHECKING:
    from privatim.models import Consultation, Meeting


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

    # Foreign keys to potential parents
    consultation_id: Mapped[UUIDStrType | None] = mapped_column(
        ForeignKey('consultations.id', ondelete='CASCADE'),
        nullable=True,
        index=True
    )
    consultation: Mapped['Consultation | None'] = relationship(
        'Consultation', back_populates='files'
    )

    meeting_id: Mapped[UUIDStrType | None] = mapped_column(
        ForeignKey('meetings.id', ondelete='CASCADE'),
        nullable=True,
        index=True
    )
    meeting: Mapped['Meeting | None'] = relationship(
        'Meeting', back_populates='files'
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

    @property
    def content_type(self) -> str:
        return self.file.content_type if self.file else ''

    @declared_attr  # type:ignore[arg-type]
    def __table_args__(cls) -> tuple[Index, ...]:
        return (
            Index(
                f'idx_{cls.__tablename__.lower()}_searchable_text_de_CH',
                'searchable_text_de_CH',
                postgresql_using='gin'
            ),
            Index('ix_searchable_files_deleted', 'deleted'),
            # Ensure exactly one parent FK is set
            CheckConstraint(
                "num_nonnulls(consultation_id, meeting_id) = 1",
                name=f'chk_{cls.__tablename__.lower()}_one_parent'
            )
        )

    # these are supported for pdfs only for now.
    pages_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def __init__(
        self,
        filename: str,
        content: bytes,
        content_type: str | None = None,
        consultation_id: UUIDStrType | None = None,
        meeting_id: UUIDStrType | None = None,
    ) -> None:
        self.id = str(uuid.uuid4())
        self.filename = filename
        self.consultation_id = consultation_id
        self.meeting_id = meeting_id

        # The database check constraint 'chk_searchable_files_one_parent'
        # ensures exactly one parent ID is non-NULL. We rely on this rather
        # than a Python check which can interfere with SQLAlchemy's loading.

        content_type = self.maybe_handle_octet_stream(
            content, content_type, filename
        )

        if content_type is None:
            content_type = self.get_content_type(content)

        if content_type == 'application/pdf':
            pages, extract = extract_pdf_info(BytesIO(content))
            self.extract = (extract or '').strip()
            self.pages_count = pages
            self.word_count = word_count(extract)
        elif content_type in word_mimetypes:
            self.extract = (get_docx_text(BytesIO(content)) or '').strip()
        elif content_type == 'text/plain':
            self.extract = content.decode('utf-8').strip()
            self.pages_count = None  # Not applicable for text files
            self.word_count = word_count(content.decode('utf-8'))
        elif content_type == 'application/octet-stream':
            self.extract = content.decode('utf-8').strip()
            self.pages_count = None  # Not applicable for text files
            self.word_count = word_count(content.decode('utf-8'))
        else:
            logger.info(f'Unsupported file type: {content_type}')
            raise ValueError(f'Unsupported file type: {content_type}')

        self.file = File(
            content=content,
            filename=filename,
            content_type=content_type,
        )

    def maybe_handle_octet_stream(
            self,
            content: bytes,
            content_type: str | None,
            filename: str
    ) -> str | None:
        """ Tries to determine the actual file if the content type is
        advertised by the request is 'application/octet-stream'. """
        if content_type is None:
            return None

        if content_type and content_type == 'application/octet-stream':
            logger.info(
                f'Got octet-stream from form file upload.'
                f'Filename' f'={filename}'
            )
            #  Saw this happen with a docx if uploading in field 'additional
            #  file'
            content_type = self.get_content_type(content)

            # Fallback to filename guess:
            if content_type == 'application/octet-stream':
                extension = filename.lower().split('.')[-1]
                if extension == 'pdf':
                    content_type = 'application/pdf'
                elif extension in ['docx', 'doc', 'docm']:
                    content_type = DEFAULT_DOCX_MIME
                elif extension == 'txt':
                    content_type = 'text/plain'
                else:
                    raise ValueError(f'Unsupported file type: {extension}')
        return content_type

    @staticmethod
    def get_content_type(content: bytes) -> str:
        """
        Determine the content type of a file using libmagic.
        """

        mime = magic.Magic(mime=True)
        file_type = mime.from_buffer(content)
        return file_type

    def __repr__(self) -> str:
        return f'<SearchableFile: {self.filename}>'
