from enum import Enum as PyEnum
from enum import IntEnum
from sqlalchemy import ForeignKey, Integer, Enum, UniqueConstraint
from privatim.orm.meta import UUIDStrPK

from sqlalchemy.orm import relationship, mapped_column, Mapped
from privatim.orm import Base
from privatim.orm.uuid_type import UUIDStr


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from privatim.models import Meeting, User


class AttendanceStatus(PyEnum):
    INVITED = 'invited'
    ATTENDED = 'attended'


class MeetingUserAttendance(Base):
    """ Stores the people of a meeting and if they attended."""

    __tablename__ = 'meetings_users_attendance'

    meeting_id: Mapped[UUIDStr] = mapped_column(
        ForeignKey('meetings.id'), primary_key=True
    )
    user_id: Mapped[UUIDStr] = mapped_column(
        ForeignKey('users.id', ondelete='SET NULL'), primary_key=True
    )

    status: Mapped[AttendanceStatus] = mapped_column(
        Enum(AttendanceStatus),
        default=AttendanceStatus.INVITED,
        nullable=False
    )

    meeting: Mapped['Meeting'] = relationship(
        "Meeting", back_populates="attendance_records"
    )
    user: Mapped['User'] = relationship(
        "User", back_populates="meeting_attendance"
    )

    def __repr__(self) -> str:
        return f'<MeetingUserAttendance {self.user_id} {self.status}>'


class AgendaItemDisplayState(IntEnum):
    COLLAPSED = 0
    EXPANDED = 1


class AgendaItemStatePreference(Base):
    """Tracks user preferences for agenda item display states
    (expanded/collapsed)"""

    __tablename__ = 'agenda_item_state_preferences'
    __table_args__ = (
        UniqueConstraint(
            'user_id', 'agenda_item_id',
            name='_user_agenda_item_uc'
        ),
    )

    id: Mapped[UUIDStrPK]

    user_id: Mapped[UUIDStr] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE')
    )

    agenda_item_id: Mapped[UUIDStr] = mapped_column(
        ForeignKey('agenda_items.id', ondelete='CASCADE')
    )

    state: Mapped[AgendaItemDisplayState] = mapped_column(
        Integer,
        default=AgendaItemDisplayState.COLLAPSED
    )

    user: Mapped['User'] = relationship(
        'User',
        back_populates='agenda_item_state_preferences'
    )

    def __repr__(self) -> str:
        return f'<AgendaItemStatePreference {self.state}>'
