from sqlalchemy import Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from privatim.models.meeting import meetings_groups_association, Meeting
from privatim.orm import Base
from privatim.orm.meta import UUIDStrPK, UUIDStr


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from privatim.models import User


class Group(Base):
    """ Defines a generic user group. """

    __tablename__ = 'groups'

    # the type of the item, this can be used to create custom polymorphic
    # subclasses of this class.
    type: 'Mapped[Text]' = mapped_column(
        Text, nullable=False, default=lambda: 'generic')

    __mapper_args__ = {
        'polymorphic_on': type,
        'polymorphic_identity': 'generic',
    }

    # the id of the user group
    id: Mapped[UUIDStrPK]

    # the name of this group
    name: 'Mapped[str | None]' = mapped_column(nullable=True)

    users: 'Mapped[User | None]' = relationship(
        'User',
        back_populates='group',
    )


class WorkingGroup(Group):
    """The working group is a more specific group compared to the
    generic group. It is used to represent a group of people working and
    having meetings together."""

    __tablename__ = 'working_groups'

    __mapper_args__ = {
        'polymorphic_identity': 'working_group',
    }

    id: Mapped[UUIDStrPK] = mapped_column(
        UUID(as_uuid=True), ForeignKey('groups.id'), primary_key=True
    )

    meetings: 'Mapped[Meeting]' = relationship(
        Meeting,
        secondary=meetings_groups_association,
        back_populates='attendees',
    )

    leader_id: Mapped[UUIDStr] = mapped_column(
         ForeignKey('user.id'), nullable=True, index=True
    )
    leader: 'Mapped[User]' = relationship(
        'User',
        foreign_keys=[leader_id],
        back_populates='leading_group',
        remote_side='User.id',
    )
