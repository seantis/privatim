import uuid
from datetime import datetime
from sedate import utcnow
from sqlalchemy import ForeignKey, Integer
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
        creator: 'User',
        description: str | None = None,
        recommendation: str | None = None,
        evaluation_result: str | None = None,
        decision: str | None = None,
        editor: 'User | None' = None,
        status: Status | None = None,
        secondary_tags: list[Tag] | None = None,
        files: list['GeneralFile'] | None = None,
        replaced_by: 'Consultation | None' = None,
        previous_version: 'Consultation | None' = None,
        is_latest_version: int = 1,
    ):
        self.id = str(uuid.uuid4())
        self.title = title
        self.description = description
        self.recommendation = recommendation
        self.evaluation_result = evaluation_result
        self.decision = decision
        self.creator = creator

        assert is_latest_version in (0, 1)
        if status is not None:
            self.status = status
        if secondary_tags is not None:
            self.secondary_tags = secondary_tags
        if files is not None:
            self.files = files

        self.editor = editor
        self.replaced_by = replaced_by
        self.previous_version = previous_version
        self.is_latest_version = is_latest_version

    id: Mapped[UUIDStrPK]
    title: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str | None] = mapped_column(nullable=True)
    recommendation: Mapped[str | None] = mapped_column(nullable=True)
    evaluation_result: Mapped[str | None] = mapped_column(nullable=True)
    decision: Mapped[str | None] = mapped_column(nullable=True)

    status: Mapped[Status | None] = relationship(
        'Status', back_populates='consultations',
    )

    created: Mapped[datetime] = mapped_column(default=utcnow)
    updated: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    secondary_tags: Mapped[list[Tag]] = relationship(
        'Tag', back_populates='consultation',
    )

    # in theory this could be nullable=False, but let's avoid problems with
    # user deletion
    creator_id: Mapped[UUIDStrType] = mapped_column(
        ForeignKey('users.id'), nullable=True
    )
    creator: Mapped['User | None'] = relationship(
        'User',
        back_populates='consultations',
        foreign_keys=[creator_id]
    )

    editor: Mapped['User | None'] = relationship(
        'User',
        foreign_keys='Consultation.editor_id'
    )
    editor_id: Mapped[UUIDStrType] = mapped_column(
        ForeignKey('users.id'), nullable=True
    )

    replaced_by: Mapped['Consultation | None'] = relationship(
        'Consultation',
        back_populates='previous_version',
        foreign_keys='Consultation.replaced_consultation_id',
        remote_side='Consultation.id'
    )
    replaced_consultation_id: Mapped[UUIDStrType] = mapped_column(
        ForeignKey('consultations.id'), nullable=True
    )
    previous_version: Mapped['Consultation | None'] = relationship(
        'Consultation',
        back_populates='replaced_by',
        foreign_keys=[replaced_consultation_id]
    )

    # Querying the latest version is undoubtedly a common operation.
    # So let's make it fast for the small price of a bit redundancy.
    # '1' means latest / '0' means not the latest
    is_latest_version: Mapped[int] = mapped_column(
        Integer, default=1, index=True,
    )

    def __acl__(self) -> list['ACL']:
        return [
            (Allow, Authenticated, ['view']),
        ]
