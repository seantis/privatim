import uuid
from datetime import datetime

from sedate import utcnow
from sqlalchemy import Text, ForeignKey, Table, Column
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import relationship

from pyramid.authorization import Allow
from pyramid.authorization import Authenticated

from privatim.orm.uuid_type import UUIDStr
from privatim.orm import Base
from privatim.orm.meta import UUIDStrPK


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from privatim.models import User, Meeting
    from privatim.types import ACL

# Many-to-many association table for users and groups

# The user record is deleted from the users table.
# In case of deleted user:
# All entries in the user_groups association table
# that reference the deleted user's id should also be deleted (CASCADE).
user_group_association: Table = Table(
    'user_groups',
    Base.metadata,
    Column('user_id', UUIDStr,
           ForeignKey('users.id', ondelete='CASCADE')),
    Column('group_id', UUIDStr, ForeignKey('groups.id')),
)


class Group(Base):
    """ Defines a generic user group. """

    __tablename__ = 'groups'

    # the type of the item, this can be used to create custom polymorphic
    # subclasses of this class.
    type: Mapped[Text] = mapped_column(
        Text, nullable=False, default=lambda: 'generic')

    __mapper_args__ = {
        'polymorphic_on': type,
        'polymorphic_identity': 'generic',
    }

    # the id of the user group
    id: Mapped[UUIDStrPK]

    # the name of this group
    name: Mapped[str] = mapped_column()

    created: Mapped[datetime] = mapped_column(default=utcnow)

    users: Mapped[list['User']] = relationship(
        'User',
        secondary=user_group_association,
        back_populates='groups',
        lazy='joined'  # we almost always want to load the associated users
    )


class WorkingGroup(Group):
    """The working group is a more specific group compared to the
    generic group. It additionally has a leader and meetings."""

    __tablename__ = 'working_groups'

    def __init__(
            self,
            name: str,
            leader: 'User | None' = None,
            meetings: list['Meeting'] | None = None,
            users: list['User'] | None = None,
            chairman_contact: str | None = None
    ):
        self.id = str(uuid.uuid4())
        self.name = name
        self.leader = leader
        self.meetings = meetings if meetings is not None else []
        self.users = users if users is not None else []
        self.chairman_contact = chairman_contact

    __mapper_args__ = {
        'polymorphic_identity': 'working_group',
    }

    id: Mapped[UUIDStrPK] = mapped_column(
         ForeignKey('groups.id'), primary_key=True
    )

    leader_id: Mapped[UUIDStr | None] = mapped_column(
        ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )
    leader: Mapped['User | None'] = relationship(
        'User',
        back_populates='leading_groups',
    )

    meetings: Mapped[list['Meeting']] = relationship(
        'Meeting', back_populates='working_group'
    )

    # Kontakt Vorstand
    chairman_contact: Mapped[str | None] = mapped_column(nullable=True)

    def __acl__(self) -> list['ACL']:
        return [
            (Allow, Authenticated, ['view']),
        ]
