from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from privatim.orm import Base
from privatim.orm.meta import UUIDStrPK, UUIDStr


class Status(Base):
    __tablename__ = "status"
    id: 'Mapped[UUIDStrPK]'
    name: Mapped[Text] = mapped_column(Text, nullable=False)
    consultations = relationship(
        "Consultation", back_populates="status"
    )


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
    status = relationship(
        "Status", back_populates="consultations"
    )

    # todo: documents
