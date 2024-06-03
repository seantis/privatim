from datetime import datetime
from sedate import utcnow
from privatim.orm import Base
from privatim.orm.associable import associated, Associable
from sqlalchemy.orm import relationship, Mapped, mapped_column, foreign, remote
from privatim.orm.meta import UUIDStrPK, UUIDStr
from sqlalchemy import Text, ForeignKey, Index, and_


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from privatim.models import User


class Comment(Base, Associable):
    """A comment that can be attached to any model."""

    __tablename__ = 'comments'

    id: Mapped[UUIDStrPK] = mapped_column(primary_key=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created: Mapped[datetime] = mapped_column(default=utcnow)
    modified: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    # Author of the comment. Nullable because the user might be deleted.
    user_id: Mapped[UUIDStr] = mapped_column(
        ForeignKey('users.id'),
        nullable=True,
    )
    user: Mapped['User'] = relationship(
        'User',
        back_populates='comments',
    )

    parent_id: Mapped[str] = mapped_column(
        ForeignKey('comments.id'), nullable=True
    )
    parent: Mapped['Comment'] = relationship(
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

    upvotes: Mapped[int] = mapped_column(default=0, nullable=False)

    def __repr__(self) -> str:
        return f'<Comment id={self.id}; content={self.content}>'

    __table_args__ = (
        Index('ix_comments_parent_id', 'parent_id'),
        Index('ix_comments_user_id', 'user_id'),
        Index('ix_comments_user_parent', 'user_id', 'parent_id'),
    )


class Commentable:
    """ Use this in your model to attach a list[Comment] """

    comments = associated(Comment, 'comments')
