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


class AbstractFile(Base):
    __abstract__ = True

    id: Mapped[UUIDStrPK] = mapped_column(primary_key=True)
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
    def name(self) -> str:
        return self.filename

    def __acl__(self) -> list['ACL']:
        return [
            (Allow, Authenticated, ['view']),
        ]
