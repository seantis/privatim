from sqlalchemy import Column, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from privatim.orm import Base
from privatim.orm.meta import UUIDStrPK, UUIDStr


class Statement(Base):
    """Stellungsnahme"""

    __tablename__ = 'statement'

    id: Mapped[UUIDStrPK]

    text = Column(Text)

    drafted_by: Mapped[UUIDStr] = mapped_column(ForeignKey('user.id'))
