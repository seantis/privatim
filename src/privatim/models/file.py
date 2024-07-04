from sqlalchemy.orm import Mapped, mapped_column, deferred
from privatim.orm.abstract import AbstractFile
from privatim.orm.meta import UUIDStrPK
from sqlalchemy import Text, ForeignKey, Integer


class GeneralFile(AbstractFile):
    """A general file (image, document, pdf, etc), referenced in the database.

    A thin wrapper around the `File` from sqlalchemy-file so that we can easily
    route to the file via the usual pathway i.e. create_uuid_factory.

    """

    __tablename__ = 'general_files'

    __mapper_args__ = {
        'polymorphic_identity': 'general_file',
    }


class SearchableFile(AbstractFile):
    """
    A file with the intention of being searchable. Should to be used with
    SearchableAssociatedFiles.
    """

    __tablename__ = 'searchable_files'

    __mapper_args__ = {
        'polymorphic_identity': 'searchable_file',
    }
    id: Mapped[UUIDStrPK] = mapped_column(
        ForeignKey('general_files.id'), primary_key=True
    )

    # the content of the given file as text.
    # (it is important that this column be loaded deferred by default, lest
    # we load massive amounts of text on simple queries)
    extract: Mapped[str] = deferred(mapped_column(Text, nullable=True))

    pages_count: Mapped[int] = mapped_column(Integer, nullable=True)

    word_count: Mapped[int] = mapped_column(Integer, nullable=True)
