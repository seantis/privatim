import uuid
from datetime import datetime

from sedate import utcnow
from sqlalchemy import ForeignKey, Integer, Index, ARRAY, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pyramid.authorization import Allow
from pyramid.authorization import Authenticated

from privatim.models.searchable import SearchableMixin
from privatim.models.soft_delete import SoftDeleteMixin
from privatim.orm import Base

from privatim.orm.meta import UUIDStrPK
from privatim.orm.meta import UUIDStr as UUIDStrType
from privatim.models.comment import Comment


from typing import TYPE_CHECKING, Iterator
if TYPE_CHECKING:
    from privatim.types import ACL
    from privatim.orm import FilteredSession
    from sqlalchemy.orm import InstrumentedAttribute
    from privatim.models import User
    from privatim.models.file import SearchableFile


class Consultation(Base, SearchableMixin, SoftDeleteMixin):
    """Vernehmlassung (Verfahren der Stellungnahme zu einer öffentlichen
    Frage)"""

    __tablename__ = 'consultations'

    def __init__(
        self,
        title: str,
        creator: 'User | None' = None,
        description: str | None = None,
        recommendation: str | None = None,
        evaluation_result: str | None = None,
        decision: str | None = None,
        editor: 'User | None' = None,
        status: str | None = None,
        files: list['SearchableFile'] | None = None,
        replaced_by: 'Consultation | None' = None,
        secondary_tags: list[str] | None = None,
        previous_version: 'Consultation | None' = None,
        comments: list[Comment] | None = None,
        is_latest_version: int = 1,
    ):

        self.id = str(uuid.uuid4())
        self.title = title
        self.description = description
        self.recommendation = recommendation
        self.evaluation_result = evaluation_result
        self.decision = decision
        if creator is not None:
            self.creator = creator

        assert is_latest_version in (0, 1)

        if status is None:
            self.status = 'Created'
        else:
            self.status = status
        self.secondary_tags = secondary_tags or []
        if files is not None:
            self.files = files

        self.editor = editor
        self.replaced_by = replaced_by
        self.previous_version = previous_version
        if comments is not None:
            self.comments = comments
        self.is_latest_version = is_latest_version

    id: Mapped[UUIDStrPK]
    title: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str | None] = mapped_column(nullable=True)
    recommendation: Mapped[str | None] = mapped_column(nullable=True)
    evaluation_result: Mapped[str | None] = mapped_column(nullable=True)
    decision: Mapped[str | None] = mapped_column(nullable=True)

    status: Mapped[str] = mapped_column(
        String(256), nullable=False, default='Created'
    )
    secondary_tags: Mapped[list[str]] = mapped_column(
        ARRAY(String(32)), nullable=False, default=list
    )

    created: Mapped[datetime] = mapped_column(default=utcnow)

    @property
    def updated(self) -> datetime:
        # This is ok, because we create a new consultation for each edit.
        # Keep the same interface (hide the implementation detail)
        return self.created

    # in theory this could be nullable=False, but let's avoid problems with
    # user deletion
    creator_id: Mapped[UUIDStrType] = mapped_column(
        ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )
    creator: Mapped['User | None'] = relationship(
        'User',
        back_populates='consultations',
        foreign_keys=[creator_id],
        passive_deletes=True
    )

    editor_id: Mapped[UUIDStrType] = mapped_column(
        ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )
    editor: Mapped['User | None'] = relationship(
        'User',
        foreign_keys='Consultation.editor_id',
        passive_deletes=True
    )

    replaced_consultation_id: Mapped[UUIDStrType] = mapped_column(
        ForeignKey('consultations.id', ondelete='CASCADE'),
        nullable=True
    )

    replaced_by: Mapped['Consultation | None'] = relationship(
        'Consultation',
        back_populates='previous_version',
        foreign_keys=[replaced_consultation_id],
        remote_side='Consultation.id',
        cascade='all, delete'
    )
    previous_version: Mapped['Consultation | None'] = relationship(
        'Consultation',
        back_populates='replaced_by',
        foreign_keys='Consultation.replaced_consultation_id',
        cascade='all, delete'
    )

    comments: Mapped[list[Comment]] = relationship(
        'Comment',
        primaryjoin="and_(Consultation.id == foreign(Comment.target_id), "
                    "Comment.target_type == 'consultations')",
        cascade='all, delete-orphan'
    )

    def add_comment(self, comment: Comment) -> None:
        # Comments should be added though no other way but this method
        comment.target_id = self.id
        comment.target_type = self.__tablename__
        self.comments.append(comment)

    # Querying the latest version is undoubtedly a common operation.
    # So let's make it fast for the small price of a bit redundancy.
    # '1' means latest / '0' means not the latest
    is_latest_version: Mapped[int] = mapped_column(
        Integer, default=1, index=True,
    )

    def is_latest(self) -> bool:
        # cosmetics
        return self.is_latest_version == 1

    def get_latest_version(self, session: 'FilteredSession') -> 'Consultation':
        if self.is_latest():
            return self
        with session.no_consultation_filter():
            latest_version = self.replaced_by
            while latest_version and not latest_version.is_latest():
                latest_version = latest_version.replaced_by
        # if we're not the latest version, there exists a newer version and
        # with that a replaced_by
        assert latest_version is not None
        return latest_version

    files: Mapped[list['SearchableFile']] = relationship(
        'SearchableFile',
        back_populates='consultation',
        cascade='all, delete-orphan'
    )

    @classmethod
    def searchable_fields(
        cls,
    ) -> 'Iterator[InstrumentedAttribute[str | None]]':
        for field in [cls.title, cls.description, cls.recommendation]:
            if field is not None:
                yield field

    def __repr__(self) -> str:
        return (
            f'<Consultation {self.title}'
        )

    def __acl__(self) -> list['ACL']:
        return [
            (Allow, Authenticated, ['view']),
        ]

    __table_args__ = (
        Index('ix_consultations_deleted', 'deleted'),
    )
