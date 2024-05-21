from uuid import uuid4

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Table, Column, ForeignKey
from sqlalchemy.orm import relationship
from pyramid.authorization import Allow
from pyramid.authorization import Authenticated
from privatim.orm.uuid_type import UUIDStr
from privatim.orm import Base
from privatim.orm.meta import UUIDStrPK, DateTimeWithTz


from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from privatim.models import User, WorkingGroup
    from datetime import datetime
    from privatim.types import ACL


meetings_users_association = Table(
    'meetings_users_association', Base.metadata,
    Column(
        'meeting_id',
        UUIDStr,
        ForeignKey('meetings.id'),
        primary_key=True
    ),
    Column(
        'user_id',
        UUIDStr,
        ForeignKey('users.id'),
        primary_key=True
    )
)


class AgendaItem(Base):
    """ Traktanden """

    __tablename__ = 'agenda_items'

    id: Mapped[UUIDStrPK]

    title: Mapped[str] = mapped_column(Text, nullable=False)

    description: Mapped[str] = mapped_column(Text)

    meeting_id: Mapped[UUIDStr] = mapped_column(
        ForeignKey('meetings.id'),
        index=True,
    )

    meeting: Mapped['Meeting'] = relationship(
        'Meeting',
        back_populates='agenda_items',
    )

    def __acl__(self) -> list['ACL']:
        return [
            (Allow, Authenticated, ['view']),
        ]


class Meeting(Base):
    """Sitzung"""

    __tablename__ = 'meetings'

    def __init__(
            self,
            name: str,
            time: 'datetime',
            attendees: list['User'],
            working_group: 'WorkingGroup'
    ):
        self.id = str(uuid4())
        self.name = name
        self.time = time
        self.attendees = attendees
        self.working_group = working_group

    id: Mapped[UUIDStrPK]

    name: Mapped[str] = mapped_column(nullable=False)

    time: Mapped[DateTimeWithTz] = mapped_column(nullable=False)

    attendees: Mapped[list['User']] = relationship(
        'User',
        secondary=meetings_users_association,
        back_populates='meetings'
    )

    # Trantanden (=Themen)
    agenda_items: Mapped[list[AgendaItem]] = relationship(
        AgendaItem,
        back_populates='meeting',
    )

    # allfällige Beschlüsse
    decisions: Mapped[str | None] = mapped_column()

    working_group_id: Mapped[UUIDStr] = mapped_column(
        ForeignKey('working_groups.id'), index=True
    )
    working_group: Mapped['WorkingGroup'] = relationship(
        'WorkingGroup', back_populates='meetings'
    )

    # todo: does this also want documents?

    def __acl__(self) -> list['ACL']:
        return [
            (Allow, Authenticated, ['view']),
        ]
