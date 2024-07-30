import uuid
from datetime import datetime
from datetime import timedelta
from sedate import utcnow
from sqlalchemy import ForeignKey
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Mapped

from privatim.orm.meta import Base, UUIDStr, UUIDStrPK, str_32, str_64


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .user import User


class TAN(Base):

    __tablename__ = 'tans'

    id: Mapped[UUIDStrPK]
    user_id: Mapped[UUIDStr] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'),
        index=True
    )
    time_requested: Mapped[datetime]
    time_expired: Mapped[datetime | None]
    tan: Mapped[str_64] = mapped_column(index=True)
    ip_address: Mapped[str_32]

    user: Mapped['User'] = relationship()

    def __init__(
            self,
            user: 'User',
            tan: str,
            ip_address: str,
            requested: datetime | None = None
    ):
        self.id = str(uuid.uuid4())
        self.user = user
        self.ip_address = ip_address
        if not requested:
            requested = utcnow()
        self.time_requested = requested
        self.time_expired = None
        self.tan = tan

    def expired(self, hours: int | None = 72) -> bool:
        now = utcnow()
        if self.time_expired and self.time_expired < now:
            return True

        if hours is not None:
            expiring_time = self.time_requested + timedelta(hours=hours)
            if now > expiring_time:
                return True
        return False

    def expire(self) -> None:
        if self.time_expired is not None:
            raise ValueError('TAN already expired')
        self.time_expired = utcnow()
