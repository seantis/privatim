import uuid
from sqlalchemy_file import File
from sqlalchemy import ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pyramid.authorization import Allow
from pyramid.authorization import Authenticated
from privatim.orm.meta import UUIDStrPK, UUIDStr, AttachedFile, Text, Base


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from privatim.models import Consultation
    from privatim.types import ACL


class ConsultationDocument(Base):
    """ File attached to a Consultation """
    __tablename__ = 'consultation_assets'

    __table_args__ = (
        UniqueConstraint('filename', 'consultation_id'),
        Index('ix_consultation_id', 'consultation_id'),
    )

    id: Mapped[UUIDStrPK]

    filename: Mapped[Text]
    """
    Name of the uploaded file. Should include a file extension to aid detecting
    the file type.
    """

    file: Mapped[AttachedFile]

    consultation_id: Mapped[UUIDStr] = mapped_column(
        ForeignKey('consultations.id')
    )
    """
    Associated consultation that this document belongs to.
    """

    consultation: Mapped['Consultation'] = relationship()

    def __init__(self, name: str, content: bytes) -> None:
        self.id = str(uuid.uuid4())
        self.filename = name
        self.file = File(content, name)

    @property
    def content(self) -> bytes:
        return self.file.file.read()

    @property
    def content_type(self) -> str:
        """ Asset's MIME type.  """
        return self.file['content_type']

    def __acl__(self) -> list['ACL']:
        return [
            (Allow, Authenticated, ['view']),
        ]
