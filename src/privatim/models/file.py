import uuid
from sqlalchemy_file import File
from sqlalchemy.orm import Mapped, mapped_column, deferred
from privatim.orm.abstract import AbstractFile
from privatim.orm.associable import Associable
from sqlalchemy import Text, Integer


class GeneralFile(AbstractFile, Associable):
    """A general file (image, document, pdf, etc), referenced in the database.

    A thin wrapper around the `File` from sqlalchemy-file so that we can easily
    route to the file via the usual pathway i.e. create_uuid_factory.

    """

    __tablename__ = 'general_files'

    __mapper_args__ = {
        'polymorphic_identity': 'general_file',
    }


class SearchableFile(AbstractFile, Associable):
    """
    A file with the intention of being searchable. Should to be used with
    SearchableAssociatedFiles.
    """

    __tablename__ = 'searchable_files'

    __mapper_args__ = {
        'polymorphic_identity': 'searchable_file',
    }

    def __init__(self, filename: str, content: bytes) -> None:
        self.id = str(uuid.uuid4())
        self.filename = filename
        self.file = File(content=content, filename=filename)

    # the content of the given file as text.
    # (it is important that this column be loaded deferred by default, lest
    # we load massive amounts of text on simple queries)
    extract: Mapped[str] = deferred(mapped_column(Text, nullable=True))

    pages_count: Mapped[int] = mapped_column(Integer, nullable=True)

    word_count: Mapped[int] = mapped_column(Integer, nullable=True)
