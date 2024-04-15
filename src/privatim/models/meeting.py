from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Table, Column, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from privatim.orm import Base
from privatim.orm.meta import UUIDStrPK, DateTimeWithoutTz


meetings_groups_association = Table(
    'meetings_groups_association',
    Base.metadata,
    Column(
        'meetings_id',
        UUID(as_uuid=True),
        ForeignKey('meetings.id'),
        primary_key=True,
    ),
    Column(
        'working_groups_id',
        UUID(as_uuid=True),
        ForeignKey('working_groups.id'),
        primary_key=True,
    ),
    Column(
        'groups_id',
        UUID(as_uuid=True),
        ForeignKey('groups.id'),
        primary_key=True,
    ),
)


class AgendaItem(Base):
    """Represents an agenda item within a meeting."""
    __tablename__ = "agenda_item"

    id: Mapped[UUIDStrPK]

    title: Mapped[str] = mapped_column(Text, nullable=False)

    description: Mapped[str] = mapped_column(Text)

    meeting_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('meetings.id'),
        index=True,
    )

    meeting: Mapped[list['Meeting']] = relationship(
        "Meeting",
        back_populates="agenda_items",
    )


class Meeting(Base):
    """Sitzung"""

    __tablename__ = "meetings"

    id: Mapped[UUIDStrPK]

    title: Mapped[str] = mapped_column(Text, nullable=False)

    time: Mapped[DateTimeWithoutTz] = mapped_column('time', nullable=False)

    attendees = relationship(
        "WorkingGroup",
        secondary=meetings_groups_association,
        back_populates="meetings"
    )

    # allfällige Beschlüsse
    decisions: Mapped[str] = mapped_column(Text)

    # Trantanden (=Themen)
    agenda_items: Mapped[list[AgendaItem]] = relationship(
        AgendaItem,
        back_populates="meeting",
    )

    # todo: documents?
