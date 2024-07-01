from datetime import datetime
from sedate import utcnow
from sqlalchemy import Text, ForeignKey
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship, deferred
from pyramid.authorization import Allow
from pyramid.authorization import Authenticated

from privatim.models.associated_file import AssociatedFiles
from privatim.models.commentable import Commentable
from privatim.models.searchable import SearchableMixin
from privatim.orm import Base
from privatim.orm.meta import UUIDStrPK
from privatim.orm.meta import UUIDStr as UUIDStrType


from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:
    from privatim.types import ACL
    from privatim.models import User


class Status(Base):
    __tablename__ = 'status'
    id: Mapped[UUIDStrPK]
    name: Mapped[Text] = mapped_column(Text, nullable=False)
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
    id: Mapped[UUIDStrPK]
    name: Mapped[Text] = mapped_column(Text, nullable=False)

    consultation: Mapped['Consultation'] = relationship(
        'Consultation', back_populates='secondary_tags',
    )
    consultation_id: Mapped[UUIDStrType] = mapped_column(
        ForeignKey('consultations.id'),
        nullable=True
    )


class Consultation(Base, Commentable, AssociatedFiles, SearchableMixin):
    """Vernehmlassung (Verfahren der Stellungnahme zu einer öffentlichen
    Frage)"""

    __tablename__ = 'consultations'

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

    creator: Mapped['User'] = relationship(
        'User',
        back_populates='consultations',
    )
    # in theory this could be nullable=False, but let's avoid problems with
    # user deletion
    creator_id: Mapped[UUIDStrType] = mapped_column(
        ForeignKey('users.id'), nullable=True
    )

    # searchable attachment texts
    searchable_text_de_CH: Mapped[str] = deferred(mapped_column(TSVECTOR))

    @classmethod
    def searchable_fields(cls) -> Iterator[str]:
        yield 'title'
        yield 'description'
        yield 'recommendation'

    def __repr__(self) -> str:
        return (
            f'<Consultation {self.title} searchable: '
            f'{self.searchable_text_de_CH}>'
        )

    def __acl__(self) -> list['ACL']:
        return [
            (Allow, Authenticated, ['view']),
        ]
