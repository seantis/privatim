
from sqlalchemy import Column, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from privatim.orm import Base
from privatim.orm.meta import UUIDStrPK, UUIDStr


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from privatim.models import User


class Statement(Base):
    """Stellungsnahme"""

    __tablename__ = 'statement'

    id: Mapped[UUIDStrPK]

    text = Column(Text)

    drafted_by: Mapped[UUIDStr] = mapped_column(ForeignKey('user.id'))
    drafter: Mapped['User'] = relationship(
        'User',
        back_populates='statements',
        foreign_keys=[drafted_by]
    )
