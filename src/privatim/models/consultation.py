import uuid
from datetime import datetime
from sedate import utcnow
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pyramid.authorization import Allow
from pyramid.authorization import Authenticated

from privatim.models.associated_file import SearchableAssociatedFiles
from privatim.models.commentable import Commentable
from privatim.models.searchable import SearchableMixin
from privatim.orm import Base
from privatim.orm.meta import UUIDStrPK
from privatim.orm.meta import UUIDStr as UUIDStrType


from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:
    from privatim.types import ACL
    from sqlalchemy.orm import InstrumentedAttribute
    from privatim.models import User
    from privatim.models.file import SearchableFile


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


class Consultation(
    Base, Commentable, SearchableAssociatedFiles, SearchableMixin
):
    """Vernehmlassung (Verfahren der Stellungnahme zu einer öffentlichen
    Frage)"""

    __tablename__ = 'consultations'

    def __init__(
        self,
        title: str,
        description: str,
        recommendation: str,
        creator: 'User',
        status: Status | None = None,
        secondary_tags: list[Tag] | None = None,
        files: list['SearchableFile'] | None = None
    ):
        self.id = str(uuid.uuid4())
        self.title = title
        self.description = description
        self.recommendation = recommendation
        if status is not None:
            self.status = status
        if secondary_tags is not None:
            self.secondary_tags = secondary_tags
        self.creator = creator
        if files is not None:
            self.files = files

    id: Mapped[UUIDStrPK]

    title: Mapped[str] = mapped_column(nullable=False)

    description: Mapped[str]

    recommendation: Mapped[str]

    status: Mapped[Status | None] = relationship(
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

    @classmethod
    def searchable_fields(cls) -> Iterator['InstrumentedAttribute[str]']:
        yield cls.title
        yield cls.description
        yield cls.recommendation

    def __repr__(self) -> str:
        return (
            f'<Consultation {self.title}, searchable_text_de_CH: '
            f'{self.searchable_text_de_CH}>'
        )

    def __acl__(self) -> list['ACL']:
        return [
            (Allow, Authenticated, ['view']),
        ]
