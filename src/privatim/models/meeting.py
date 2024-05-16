from uuid import uuid4
from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Table, Column, ForeignKey
from sqlalchemy.orm import relationship

from privatim.orm.uuid_type import UUIDStr
from privatim.orm import Base
from privatim.orm.meta import UUIDStrPK, DateTimeWithTz


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from privatim.models import User
    from datetime import datetime


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

    meeting: Mapped[list['Meeting']] = relationship(
        'Meeting',
        back_populates='agenda_items',
    )


class Meeting(Base):
    """Sitzung"""

    __tablename__ = 'meetings'

    def __init__(
            self,
            name: str,
            time: 'datetime',
            attendees: list['User'],
    ):
        self.id = str(uuid4())
        self.name = name
        self.time = time
        self.attendees = attendees

    id: Mapped[UUIDStrPK]

    name: Mapped[str] = mapped_column(nullable=False)

    time: Mapped[DateTimeWithTz] = mapped_column(nullable=False)

    attendees: Mapped[list['User']] = relationship(
        'User',
        secondary=meetings_users_association,
        back_populates='meetings'
    )

    # allfällige Beschlüsse
    decisions: Mapped[str | None] = mapped_column()

    # Trantanden (=Themen)
    agenda_items: Mapped[list[AgendaItem]] = relationship(
        AgendaItem,
        back_populates='meeting',
    )

    # todo: documents
