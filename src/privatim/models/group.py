from uuid import uuid4

from sqlalchemy import Column, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from privatim.models.meeting import meetings_groups_association
from privatim.orm import Base


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from privatim.models import User
    from sqlalchemy.orm import AppenderQuery


class Group(Base):
    """ Defines a generic user group. """

    __tablename__ = 'groups'

    #: the type of the item, this can be used to create custom polymorphic
    #: subclasses of this class.
    type: 'Mapped[str]' = mapped_column(
        Text, nullable=False, default=lambda: 'generic')

    __mapper_args__ = {
        'polymorphic_on': type,
        'polymorphic_identity': 'generic',
    }

    #: the id of the user group

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    #: the name of this group
    name: 'Column[Text | None]' = Column(Text, nullable=True)

    if TYPE_CHECKING:
        # forward declare backref
        users: relationship[AppenderQuery[User]]


class WorkingGroup(Group):
    """A working group."""

    __tablename__ = "working_groups"

    __mapper_args__ = {
        'polymorphic_identity': 'working_group',
    }

    id = Column(UUID(as_uuid=True), ForeignKey('groups.id'), primary_key=True)

    # Relationship to Meeting
    meetings = relationship(
        "Meeting",
        secondary=meetings_groups_association,
        back_populates="attendees",
    )

    # todo: add leader of group
    # leader_id = mapped_column(UUID, ForeignKey("user.id"), unique=True)
    #
    # leader = relationship(
    #     "User",
    #     back_populates="leading_group",
    #     uselist=False,
    # )
