from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
import bcrypt
from sedate import utcnow
from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import Mapped, backref
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from privatim.models import Group
from privatim.orm import Base
from privatim.orm.meta import UUIDStrPK, str_256, str_128, UUIDStr

from typing import TypeAlias, Literal, TYPE_CHECKING
if TYPE_CHECKING:
    PersonType: TypeAlias = Literal['internal', 'external']


class User(Base):
    __tablename__ = "user"

    id: Mapped[UUIDStrPK]

    first_name: Mapped[str_256 | None]
    last_name: Mapped[str_256 | None]
    email: Mapped[str_256] = mapped_column(unique=True)
    password: Mapped[str_128 | None]
    last_login: Mapped[datetime | None]
    last_password_change: Mapped[datetime | None]
    created: Mapped[datetime] = mapped_column(default=utcnow)
    modified: Mapped[datetime | None] = mapped_column(onupdate=utcnow)

    # the group this user belongs to
    group_id: 'Column[UUIDStr | None]' = Column(
        UUID,  # type:ignore[arg-type]
        ForeignKey(Group.id),
        nullable=True
    )
    group: 'Mapped[list[Group | None]]' = relationship(
        Group, backref=backref('users', lazy='dynamic')
    )

    def set_password(self, password: str) -> None:
        password = password or ''
        pwhash = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())
        self.password = pwhash.decode('utf8')
        self.last_password_change = utcnow()

    def check_password(self, password: str) -> bool:
        if not self.password:
            return False
        try:
            return bcrypt.checkpw(
                password.encode("utf8"), self.password.encode("utf8")
            )
        except (AttributeError, ValueError):
            return False
