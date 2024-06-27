import uuid
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from privatim.orm import Base
from privatim.orm.meta import UUIDStrPK, UUIDStr


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from privatim.models import User


class Statement(Base):
    """Stellungsnahme"""

    __tablename__ = 'statements'

    def __init__(
            self,
            text: str,
            drafter: 'User',
    ):
        self.id = str(uuid.uuid4())
        self.text = text
        self.drafter = drafter

    id: Mapped[UUIDStrPK]

    text: Mapped[str]

    drafted_by: Mapped[UUIDStr] = mapped_column(ForeignKey('users.id'))
    drafter: Mapped['User'] = relationship(
        'User',
        back_populates='statements',
        foreign_keys=[drafted_by]
    )
