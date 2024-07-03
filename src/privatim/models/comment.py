import uuid
from datetime import datetime
from sedate import utcnow
from privatim.orm import Base
from privatim.orm.associable import Associable
from privatim.models import SearchableMixin
from sqlalchemy.orm import (
    relationship,
    Mapped,
    mapped_column,
    foreign,
    remote,
)
from privatim.orm.meta import UUIDStrPK, UUIDStr
from sqlalchemy import Text, ForeignKey, Index, and_


from typing import Iterator
from typing import TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from privatim.models import User
    from sqlalchemy.orm import InstrumentedAttribute


class Comment(Base, Associable, SearchableMixin):
    """A generic comment that shall be attachable to any model.
    Meant to be used in conjunction with `Commentable`.

    class Commentable:
        comments = associated(Comment, 'comments')

    class YourModel(Base, Commentable):
        name: Mapped[str]
        ...

    model = YourModel(name='stuff')
    model.comments.append(Comment('Interesting sqlalchemy design pattern'))

   """

    __tablename__ = 'comments'

    def __init__(
        self,
        content: str,
        user: 'User',
        parent: Optional['Comment'] = None
    ):
        self.id = str(uuid.uuid4())
        self.content = content
        self.user = user
        self.parent = parent

    id: Mapped[UUIDStrPK] = mapped_column(primary_key=True)

    content: Mapped[str] = mapped_column(Text, nullable=False)
    created: Mapped[datetime] = mapped_column(default=utcnow)
    modified: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    # Author of the comment. Nullable because the user might be deleted.
    user_id: Mapped[UUIDStr] = mapped_column(
        ForeignKey('users.id'),
        nullable=True,
    )
    user: Mapped['User | None'] = relationship(
        'User',
        back_populates='comments',
    )

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

    def __repr__(self) -> str:
        return f'<Comment id={self.id}; content={self.content}>'

    @classmethod
    def searchable_fields(cls) -> Iterator['InstrumentedAttribute[str]']:
        yield cls.content

    __table_args__ = (
        Index('ix_comments_parent_id', 'parent_id'),
        Index('ix_comments_user_id', 'user_id'),
        Index('ix_comments_user_parent', 'user_id', 'parent_id'),
    )
