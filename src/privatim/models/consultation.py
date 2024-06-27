import uuid
from datetime import datetime
from sedate import utcnow
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pyramid.authorization import Allow
from pyramid.authorization import Authenticated

from privatim.models.associated_file import AssociatedFiles
from privatim.models.commentable import Commentable
from privatim.orm import Base
from privatim.orm.meta import UUIDStrPK
from privatim.orm.meta import UUIDStr as UUIDStrType


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from privatim.types import ACL
    from privatim.models import User, GeneralFile


class Status(Base):
    __tablename__ = 'status'

    def __init__(
            self,
            name: str,
    ):
        self.id = str(uuid.uuid4())
        self.name = name

    id: Mapped[UUIDStrPK]

    name: Mapped[str] = mapped_column(nullable=False)
    consultations = relationship(
        'Consultation', back_populates='status'
    )
    consultation_id: Mapped[UUIDStrType] = mapped_column(
        ForeignKey('consultations.id'),
        nullable=True
    )

    def __repr__(self) -> str:
        return f'<Status {self.name}>'


class Tag(Base):

    __tablename__ = 'secondary_tags'

    def __init__(
        self,
        name: str,
    ):
        self.id = str(uuid.uuid4())
        self.name = name

    id: Mapped[UUIDStrPK]

    name: Mapped[str] = mapped_column(nullable=False)

    consultation: Mapped['Consultation'] = relationship(
        'Consultation', back_populates='secondary_tags',
    )
    consultation_id: Mapped[UUIDStrType] = mapped_column(
        ForeignKey('consultations.id'),
        nullable=True
    )


class Consultation(Base, Commentable, AssociatedFiles):
    """Vernehmlassung (Verfahren der Stellungnahme zu einer öffentlichen
    Frage)"""

    __tablename__ = 'consultations'

    def __init__(
        self,
        title: str,
        description: str,
        recommendation: str,
        status: Status,
        secondary_tags: list[Tag],
        creator: 'User',
        files: list['GeneralFile'] | None = None
    ):
        self.id = str(uuid.uuid4())
        self.title = title
        self.description = description
        self.recommendation = recommendation
        self.status = status
        self.secondary_tags = secondary_tags
        self.creator = creator
        if files is not None:
            self.files = files

    id: Mapped[UUIDStrPK]

    title: Mapped[str] = mapped_column(nullable=False)

    description: Mapped[str]

    recommendation: Mapped[str]

    status: Mapped[Status] = relationship(
        'Status', back_populates='consultations',
    )

    created: Mapped[datetime] = mapped_column(default=utcnow)

    secondary_tags: Mapped[list[Tag]] = relationship(
        'Tag', back_populates='consultation',
    )

    creator: Mapped['User | None'] = relationship(
        'User',
        back_populates='consultations',
    )
    # in theory this could be nullable=False, but let's avoid problems with
    # user deletion
    creator_id: Mapped[UUIDStrType] = mapped_column(
        ForeignKey('users.id'), nullable=True
    )

    def __acl__(self) -> list['ACL']:
        return [
            (Allow, Authenticated, ['view']),
        ]
