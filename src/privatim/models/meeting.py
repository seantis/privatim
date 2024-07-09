import uuid
from sqlalchemy import Text, Integer, select, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Table, Column, ForeignKey
from sqlalchemy.orm import relationship
from pyramid.authorization import Allow
from pyramid.authorization import Authenticated
from privatim.models import SearchableMixin
from privatim.models.commentable import Commentable
from privatim.orm.uuid_type import UUIDStr
from privatim.orm import Base
from privatim.orm.meta import UUIDStrPK, DateTimeWithTz
from privatim.utils import maybe_escape


from typing import TYPE_CHECKING, Iterator
if TYPE_CHECKING:
    from privatim.models import User, WorkingGroup
    from datetime import datetime
    from privatim.types import ACL
    from sqlalchemy.orm import Session
    from sqlalchemy.orm import InstrumentedAttribute


class AgendaItemCreationError(Exception):
    """Custom exception for errors in creating AgendaItem instances."""
    pass


meetings_users_association: Table = Table(
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


class AgendaItem(Base, SearchableMixin):
    """ Traktanden """

    __tablename__ = 'agenda_items'

    def __init__(
        self,
        title: str,
        description: str,
        meeting: 'Meeting',
        position: int,
    ):
        if position is None:
            raise AgendaItemCreationError(
                'AgendaItem objects must be created using the create class '
                'method because the attribute `position` has to be set.'
            )
        self.id = str(uuid.uuid4())
        self.title = title
        self.description = description
        self.meeting = meeting
        self.position = position

    @classmethod
    def create(
        cls,
        session: 'Session',
        title: str,
        description: str,
        meeting: 'Meeting'
    ) -> 'AgendaItem':

        meeting_id = meeting.id
        max_position = session.scalar(
            select(func.max(AgendaItem.position)).where(
                AgendaItem.meeting_id == meeting_id
            )
        )
        new_position = 0 if max_position is None else max_position + 1
        new_agenda_item = cls(
            title=maybe_escape(title),
            description=maybe_escape(description),
            meeting=meeting,
            position=new_position,
        )
        session.add(new_agenda_item)
        return new_agenda_item

    id: Mapped[UUIDStrPK]

    title: Mapped[str] = mapped_column(Text, nullable=False)

    # the custom order which may be changed by the user
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    description: Mapped[str] = mapped_column(Text)

    meeting_id: Mapped[UUIDStr] = mapped_column(
        ForeignKey('meetings.id'),
        index=True,
    )

    meeting: Mapped['Meeting'] = relationship(
        'Meeting',
        back_populates='agenda_items',
        order_by='AgendaItem.position'
    )

    @classmethod
    def searchable_fields(cls) -> Iterator['InstrumentedAttribute[str]']:
        yield cls.title
        yield cls.description

    def __acl__(self) -> list['ACL']:
        return [
            (Allow, Authenticated, ['view']),
        ]

    def __repr__(self) -> str:
        return f'<AgendaItem {self.title} position {self.position}>'


class Meeting(Base, SearchableMixin):
    """Sitzung"""

    __tablename__ = 'meetings'

    def __init__(
            self,
            name: str,
            time: 'datetime',
            attendees: list['User'],
            working_group: 'WorkingGroup',
            agenda_items: list[AgendaItem] | None = None,
    ):
        self.id = str(uuid.uuid4())
        self.name = maybe_escape(name)
        self.time = time
        self.attendees = attendees
        self.working_group = working_group
        if agenda_items:
            self.agenda_items = agenda_items

    id: Mapped[UUIDStrPK]

    name: Mapped[str] = mapped_column(nullable=False)

    time: Mapped[DateTimeWithTz] = mapped_column(nullable=False)

    attendees: Mapped[list['User']] = relationship(
        'User',
        secondary=meetings_users_association,
        back_populates='meetings'
    )

    # Traktanden (=Themen)
    agenda_items: Mapped[list[AgendaItem]] = relationship(
        AgendaItem,
        back_populates='meeting',
        order_by="AgendaItem.position",
        cascade="all, delete-orphan"
    )

    # allfällige Beschlüsse
    decisions: Mapped[str | None] = mapped_column()

    working_group_id: Mapped[UUIDStr] = mapped_column(
        ForeignKey('working_groups.id'), index=True
    )
    working_group: Mapped['WorkingGroup'] = relationship(
        'WorkingGroup', back_populates='meetings'
    )

    @classmethod
    def searchable_fields(cls) -> Iterator['InstrumentedAttribute[str]']:
        yield cls.name

    def __acl__(self) -> list['ACL']:
        return [
            (Allow, Authenticated, ['view']),
        ]
