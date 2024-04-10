from sqlalchemy import Column, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from privatim.orm import Base
from privatim.orm.meta import UUIDStrPK


class Consultation(Base):
    """Vernehmlassung (Verfahren der Stellungnahme zu einer öffentlichen
    Frage)"""

    __tablename__ = "consultation"

    id: Mapped[UUIDStrPK] = mapped_column()

    title = Column(String, nullable=False)

    description = Column(Text)

    # facter out into table
    status = Column(String)

    # documents

    # kommentare

    recommendation = Column(String)
