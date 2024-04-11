from sqlalchemy import Column, DateTime, Text, Table
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Table, Column, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from privatim.orm import Base
from privatim.orm.meta import UUIDStrPK

meeting_person_association = Table(
    'meeting_person',
    Base.metadata,
    Column(
        'meeting_id',
        UUID(as_uuid=True),
        ForeignKey('meeting.id'),
        primary_key=True,
    ),
    Column(
        'person_id',
        UUID(as_uuid=True),
        ForeignKey('person.id'),
        primary_key=True,
    ),
)

class Meeting(Base):
    """Sitzung"""

    __tablename__ = "meeting"

    id: Mapped[UUIDStrPK]

    description = Column(Text)

    datetime = Column(
        DateTime,
        nullable=False,
    )

    # documents

    attendees = relationship(
        "Person",
        secondary=meeting_person_association,
        backref="meetings"
    )
    # agenda_item # traktandenliste
