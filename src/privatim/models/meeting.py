from __future__ import annotations
import uuid

from sedate import utcnow
from sqlalchemy import Integer, select, func, Text, Select
from sqlalchemy.orm import Mapped, mapped_column, contains_eager
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from pyramid.authorization import Allow
from pyramid.authorization import Authenticated

from privatim.models.file import SearchableFile
from privatim.orm.meta import UUIDStr as UUIDStrType
from privatim.models import SearchableMixin
from privatim.models.association_tables import AttendanceStatus, \
    AgendaItemDisplayState, AgendaItemStatePreference
from privatim.models.association_tables import MeetingUserAttendance
from privatim.orm.uuid_type import UUIDStr
from privatim.orm import Base
from privatim.orm.meta import UUIDStrPK, DateTimeWithTz
from privatim.models.user import User


from typing import TYPE_CHECKING
from collections.abc import Iterator
if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from privatim.models import WorkingGroup
    from privatim.types import ACL
    from sqlalchemy.orm import InstrumentedAttribute
    from pyramid.interfaces import IRequest


class AgendaItemCreationError(Exception):
    """Custom exception for errors in creating AgendaItem instances."""
    pass


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
            title=title,
            description=description,
            meeting=meeting,
            position=new_position,
        )

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

    )

    @classmethod
    def searchable_fields(cls) -> Iterator['InstrumentedAttribute[str]']:
        yield cls.title
        yield cls.description

    def get_display_state_for_user(
            self,
            request: 'IRequest',
    ) -> AgendaItemDisplayState:
        session = request.dbsession
        user = request.user
        if not session:
            return AgendaItemDisplayState.COLLAPSED

        preference = session.execute(
            select(AgendaItemStatePreference).where(
                AgendaItemStatePreference.agenda_item_id
                == self.id, AgendaItemStatePreference.user_id == user.id,
            )
        ).scalar_one_or_none()
        return preference.state if preference \
            else (AgendaItemDisplayState.COLLAPSED)

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
            time: datetime,
            attendees: list[User],
            working_group: 'WorkingGroup',
            agenda_items: list[AgendaItem] | None = None,
            creator: User | None = None
    ):
        self.id = str(uuid.uuid4())
        self.name = name
        self.time = time

        # Create MeetingUserAttendance objects for each attendee
        self.attendance_records = [
            MeetingUserAttendance(
                user=attendee,
                status=AttendanceStatus.INVITED
            )
            for attendee in attendees
        ]

        self.working_group = working_group
        self.creator = creator
        if agenda_items:
            self.agenda_items = agenda_items

    id: Mapped[UUIDStrPK]

    name: Mapped[str] = mapped_column(nullable=False)

    time: Mapped[DateTimeWithTz] = mapped_column(nullable=False)

    attendance_records: Mapped[list[MeetingUserAttendance]] = relationship(
        'MeetingUserAttendance',
        back_populates='meeting',
        cascade='all, delete-orphan',
    )

    files: Mapped[list[SearchableFile]] = relationship(
        'SearchableFile',
        primaryjoin="Meeting.id == SearchableFile.meeting_id",
        cascade='all, delete-orphan',
        back_populates='meeting',
        uselist=True
    )

    @property
    def sorted_attendance_records(
            self
    ) -> Select[tuple[MeetingUserAttendance]]:
        return (
            select(MeetingUserAttendance)
            .join(MeetingUserAttendance.user)
            .filter(MeetingUserAttendance.meeting_id == self.id)
            .options(contains_eager(MeetingUserAttendance.user))
            .order_by(
                func.coalesce(User.last_name, '').desc(),
                func.coalesce(User.first_name, '').desc(),
            )
        )

    @property
    def attendees(self) -> list[User]:
        """ Returns all attendees regardless of status. """
        return [record.user for record in self.attendance_records]

    agenda_items: Mapped[list[AgendaItem]] = relationship(
        AgendaItem,
        back_populates='meeting',
        cascade='all, delete-orphan',
        order_by='AgendaItem.position'
    )

    @property
    def sorted_agenda_items(self) -> list[AgendaItem]:
        return sorted(self.agenda_items, key=lambda x: x.position)

    created: Mapped[datetime] = mapped_column(default=utcnow)
    updated: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    creator_id: Mapped[UUIDStrType] = mapped_column(
        ForeignKey('users.id', ondelete='SET NULL'), nullable=True,
    )
    creator: Mapped[User | None] = relationship(
        'User',
        back_populates='created_meetings',
        foreign_keys=[creator_id],
        passive_deletes=True
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
