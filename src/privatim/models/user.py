from datetime import datetime
from functools import cached_property

import bcrypt
from sedate import utcnow
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from privatim.models import Group, WorkingGroup
from privatim.models.group import user_group_association
from privatim.orm import Base
from privatim.orm.meta import UUIDStrPK, str_256, str_128

from typing import TypeAlias, Literal, TYPE_CHECKING
if TYPE_CHECKING:
    PersonType: TypeAlias = Literal['internal', 'external']


class User(Base):
    __tablename__ = 'user'

    id: Mapped[UUIDStrPK]

    first_name: Mapped[str_256 | None]
    last_name: Mapped[str_256 | None]
    email: Mapped[str_256] = mapped_column(unique=True)
    password: Mapped[str_128 | None]
    last_login: Mapped[datetime | None]
    last_password_change: Mapped[datetime | None]

    created: Mapped[datetime] = mapped_column(default=utcnow)
    modified: Mapped[datetime | None] = mapped_column(onupdate=utcnow)

    # the groups this user is part of
    groups: Mapped[list[Group]] = relationship(
        'Group',
        secondary=user_group_association,
        back_populates='users',
    )

    # the groups this user is a leader of
    leading_groups: Mapped[list[WorkingGroup]] = relationship(
        'WorkingGroup',
        back_populates='leader',
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
                password.encode('utf8'), self.password.encode('utf8')
            )
        except (AttributeError, ValueError):
            return False

    @cached_property
    def fullname(self) -> str:
        parts = []
        if self.first_name:
            parts.append(self.first_name)
        if self.last_name:
            parts.append(self.last_name)
        if not parts:
            return self.email
        return ' '.join(parts)
