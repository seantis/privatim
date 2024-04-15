from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from privatim.orm import Base
from privatim.orm.meta import UUIDStrPK, UUIDStr


class Status(Base):
    __tablename__ = "status"
    id: Mapped[UUIDStrPK]
    name = Column(String, nullable=False)


class Consultation(Base):
    """Vernehmlassung (Verfahren der Stellungnahme zu einer öffentlichen
    Frage)"""

    __tablename__ = "consultation"

    id: Mapped[UUIDStrPK]

    title = Column(String, nullable=False)

    description = Column(Text)

    comments = Column(Text)

    recommendation = Column(String)

    status_id: Mapped[UUIDStr] = mapped_column(
        ForeignKey('status.id'),
    )
    status: Mapped[Status] = relationship(
        "Status",
        backref="consultations",
    )

    # todo
    # documents
