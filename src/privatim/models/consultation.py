from sqlalchemy import Column, String, Text
from sqlalchemy.orm import Mapped

from privatim.orm import Base
from privatim.orm.meta import UUIDStrPK


class Consultation(Base):
    """Vernehmlassung (Verfahren der Stellungnahme zu einer öffentlichen
    Frage)"""

    __tablename__ = "consultation"

    id: Mapped[UUIDStrPK]

    title = Column(String, nullable=False)

    description = Column(Text)

    comments = Column(Text)

    recommendation = Column(String)

    # todo: facter out into table
    status = Column(String)

    # documents
