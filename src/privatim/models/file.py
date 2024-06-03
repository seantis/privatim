import uuid

from pyramid.authorization import Allow
from pyramid.authorization import Authenticated
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy_file import File
from privatim.orm.meta import UUIDStrPK, AttachedFile
from privatim.orm import Base

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from privatim.types import ACL


class GeneralFile(Base):
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

    def __acl__(self) -> list['ACL']:
        return [
            (Allow, Authenticated, ['view']),
        ]
