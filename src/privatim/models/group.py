from sqlalchemy import Text, ForeignKey, Table, Column
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import relationship

from privatim.orm.uuid_type import UUIDStr
from privatim.orm import Base
from privatim.orm.meta import UUIDStrPK


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from privatim.models import User

# Many-to-many association table for users and groups
user_group_association = Table(
    'user_groups', Base.metadata,
    Column('user_id', UUIDStr, ForeignKey('user.id')),
    Column('group_id', UUIDStr, ForeignKey('groups.id'))
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

    __mapper_args__ = {
        'polymorphic_identity': 'working_group',
    }

    id: Mapped[UUIDStrPK] = mapped_column(
         ForeignKey('groups.id'), primary_key=True
    )

    leader_id: Mapped[UUIDStr | None] = mapped_column(
        ForeignKey('user.id'), nullable=True
    )
    leader: Mapped['User'] = relationship(
        'User',
        back_populates='leading_groups',
    )
