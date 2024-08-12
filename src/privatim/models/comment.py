import uuid
from datetime import datetime
from sedate import utcnow
from privatim.orm import Base
from sqlalchemy.orm import (relationship, Mapped, mapped_column, foreign,
                            remote, object_session)
from privatim.orm.meta import UUIDStrPK, UUIDStr
from sqlalchemy import Text, ForeignKey, Index, and_, select
from privatim.models import SearchableMixin
from pyramid.authorization import Allow, DENY_ALL

from typing import TYPE_CHECKING, Optional, TypeVar, Iterator
if TYPE_CHECKING:
    from privatim.models import User
    from sqlalchemy.orm import InstrumentedAttribute, Session
    from privatim.models.consultation import Consultation
    from privatim.types import ACL
    T = TypeVar('T', bound='Base')


class Comment(Base, SearchableMixin):

    __tablename__ = 'comments'

    def __init__(
        self,
        content: str,
        user: 'User',
        target_id: str,
        target_type: str = 'consultations',
        parent: Optional['Comment'] = None

    ):
        self.id = str(uuid.uuid4())
        self.content = content
        self.user = user
        self.parent = parent
        self.target_id = target_id
        self.target_type = target_type

    id: Mapped[UUIDStrPK] = mapped_column(primary_key=True)


    content: Mapped[str] = mapped_column(Text, nullable=False)

    created: Mapped[datetime] = mapped_column(default=utcnow)
    updated: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    # Author of the comment. Nullable to be somewhat more resilient for
    # deleted users
    user_id: Mapped[UUIDStr] = mapped_column(
        ForeignKey('users.id'),
        nullable=True,
    )
    user: Mapped['User | None'] = relationship(
        'User',
        back_populates='comments',
    )

    # primary key of the model to which the comment attached itself
    target_id: Mapped[UUIDStr] = mapped_column(nullable=False)

    # Generic name of the table to which the comment attached itself
    # The reason we use this and not simple foreign key consultation,
    # is because we might want to have comments in other models in the future.
    target_type: Mapped[str] = mapped_column(nullable=False)

    parent_id: Mapped[str] = mapped_column(
        ForeignKey('comments.id'), nullable=True
    )
    parent: Mapped['Comment | None'] = relationship(
        'Comment', remote_side='Comment.id',
        back_populates='children'
    )

    children: Mapped[list['Comment']] = relationship(
        'Comment',
        back_populates='parent',
        cascade='all, delete-orphan'
    )

    siblings = relationship(
        'Comment',
        primaryjoin=and_(
            foreign(parent_id) == remote(parent_id),
            id != remote(id)
        ),
        uselist=True,
        viewonly=True
    )

    __mapper_args__ = {
        'polymorphic_on': target_type,
    }

    def get_model(self, session: 'Session') -> 'Consultation':
        """ Get the model which the comment is part of. """

        if self.target_type == 'consultations':
            from privatim.models import Consultation
            return session.execute(select(Consultation).where(
                Consultation.id == self.target_id
            )).scalar_one()
        else:
            # Leave open the possibility of adding more commentable types
            raise NotImplementedError()

    def __repr__(self) -> str:
        return f'<Comment id={self.id}; content={self.content}>'

    def __acl__(self) -> list['ACL']:
        """ This __acl__ method allows the comment owner to edit and delete
             the comment, and denies access to all other users."""
        if self.user is None:
            return [DENY_ALL]

        return [
            (Allow, str(self.user.id), ['edit', 'delete']),
            DENY_ALL
        ]

    @classmethod
    def searchable_fields(cls) -> Iterator['InstrumentedAttribute[str]']:
        yield cls.content

    __table_args__ = (
        Index('ix_comments_parent_id', 'parent_id'),
        Index('ix_comments_user_id', 'user_id'),
        Index('ix_comments_user_parent', 'user_id', 'parent_id'),
    )
