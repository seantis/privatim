import uuid

from sedate import utcnow
from sqlalchemy import Integer, select, func, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from pyramid.authorization import Allow
from pyramid.authorization import Authenticated

from privatim.orm.meta import UUIDStr as UUIDStrType
from privatim.models import SearchableMixin
from privatim.models.commentable import Commentable
from privatim.models.association_tables import AttendanceStatus
from privatim.models.association_tables import MeetingUserAttendance
from privatim.orm.uuid_type import UUIDStr
from privatim.orm import Base
from privatim.orm.meta import UUIDStrPK, DateTimeWithTz
from privatim.utils import maybe_escape


from typing import TYPE_CHECKING, Iterator, Union

if TYPE_CHECKING:
    from privatim.models import User
    from sqlalchemy.orm import Session
    from privatim.models import WorkingGroup
    from privatim.types import ACL
    from sqlalchemy.orm import InstrumentedAttribute


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


class Meeting(Base, SearchableMixin, Commentable):
    """Sitzung"""

    __tablename__ = 'meetings'

    def __init__(
            self,
            name: str,
            time: datetime,
            attendees: list['User'],
            working_group: 'WorkingGroup',
            agenda_items: list[AgendaItem] | None = None,
            creator: 'User | None' = None
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
        "MeetingUserAttendance",
        back_populates="meeting",
        cascade="all, delete-orphan",
    )

    @property
    def attendees(self) -> list['User']:
        return [record.user for record in self.attendance_records]

    def update_attendees_with_status(
        self,
        users_with_status: list[Union[tuple['User', 'AttendanceStatus'], 'User']],
    ) -> None:
        """
        Set attendees with optional status.

        :param users_with_status: List of User objects or tuples of (User, AttendanceStatus)
        """
        # Create a dictionary of existing records for efficient lookup
        existing_records = {
            str(record.user_id): record for record in self.attendance_records
        }

        new_records = []
        for item in users_with_status:
            if isinstance(item, tuple):
                user, status = item
            else:
                user = item
                status = AttendanceStatus.INVITED  # Default status if not provided

            if user.id in existing_records:
                # Update existing record
                existing_records[str(user.id)].status = status
            else:
                # Create new record
                new_records.append(MeetingUserAttendance(user=user, status=status))

        # Add new records
        self.attendance_records.extend(new_records)

        # Remove records for users not in the new list
        user_ids = {
            user.id if isinstance(user, User) else user[0].id
            for user in users_with_status
        }
        self.attendance_records = [
            record
            for record in self.attendance_records
            if record.user_id in user_ids
        ]


    agenda_items: Mapped[list[AgendaItem]] = relationship(
        AgendaItem,
        back_populates='meeting',
        order_by="AgendaItem.position",
        cascade="all, delete-orphan"
    )

    created: Mapped[datetime] = mapped_column(default=utcnow)
    updated: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    creator_id: Mapped[UUIDStrType] = mapped_column(
        ForeignKey('users.id'), nullable=True
    )
    creator: Mapped['User | None'] = relationship(
        'User',
        back_populates='created_meetings',
        foreign_keys=[creator_id]
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
