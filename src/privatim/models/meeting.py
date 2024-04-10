from sqlalchemy import Column, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from privatim.orm import Base
from privatim.orm.meta import UUIDStrPK


class Meeting(Base):
    """Sitzung"""

    __tablename__ = "meeting"

    id: Mapped[UUIDStrPK] = mapped_column()

    description = Column(Text)

    datetime = Column(
        DateTime,
        nullable=False,
    )

    # docs
    # people associated (invited/)
    # agenda_item # traktandenliste
