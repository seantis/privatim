import uuid

from pyramid.authorization import Allow
from pyramid.authorization import Authenticated
from sqlalchemy.orm import Mapped, mapped_column, deferred
from sqlalchemy_file import File

from privatim.orm.associable import Associable
from privatim.orm.meta import UUIDStrPK, AttachedFile
from sqlalchemy import Text, ForeignKey
from privatim.orm import Base

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from privatim.types import ACL


class GeneralFile(Base, Associable):
    """ A general file (image, document, pdf, etc), referenced in the database.

    A thin wrapper around the `File` from sqlalchemy-file so that we can easily
    route to the file via the usual pathway i.e. create_uuid_factory.

    """
    __tablename__ = 'general_files'

    id: Mapped[UUIDStrPK]

    file: Mapped[AttachedFile] = mapped_column(nullable=False)

    filename: Mapped[str] = mapped_column(nullable=False)

    def __init__(self, filename: str, content: bytes) -> None:
        self.id = str(uuid.uuid4())
        self.filename = filename
        self.file = File(content=content, filename=filename)

    @property
    def content(self) -> bytes:
        return self.file.file.read()

    @property
    def content_type(self) -> str:
        return self.file.content_type

    def __acl__(self) -> list['ACL']:
        return [
            (Allow, Authenticated, ['view']),
        ]


class SearchableFile(GeneralFile):
    """ A file with the intention of being searchable.$

    """
    __tablename__ = 'searchable_files'

    id: Mapped[UUIDStrPK] = mapped_column(
        ForeignKey('general_files.id'), primary_key=True
    )

    # the content of the given file as text.
    # (it is important that this column be loaded deferred by default, lest
    # we load massive amounts of text on simple queries)
    extract: Mapped[str | None] = deferred(mapped_column(Text, nullable=True))

    __mapper_args__ = {
        'polymorphic_identity': 'searchable_file',
    }

    def __init__(
        self, filename: str, content: bytes, extract: str | None = None
    ) -> None:
        super().__init__(filename, content)
        self.extract = extract
