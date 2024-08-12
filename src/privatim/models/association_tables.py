from enum import Enum as PyEnum
from sqlalchemy import Enum, Column, Table
from sqlalchemy import ForeignKey
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
    """ Stores the people of a meeting and if they attened."""

    __tablename__ = 'meetings_users_attendance'

    meeting_id: Mapped[UUIDStr] = mapped_column(
        ForeignKey('meetings.id'), primary_key=True
    )
    user_id: Mapped[UUIDStr] = mapped_column(
        ForeignKey('users.id'), primary_key=True
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
