import uuid
from functools import cached_property
from pyramid.authorization import Allow
from pyramid.authorization import Authenticated
import bcrypt
from datetime import datetime
from datetime import timezone
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from privatim.models import Group, WorkingGroup
from privatim.models.group import user_group_association
from privatim.models.meeting import meetings_users_association
from privatim.orm import Base
from privatim.orm.meta import UUIDStrPK, str_256, str_128

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from privatim.types import ACL
    from privatim.models import Meeting


class User(Base):
    __tablename__ = 'users'

    id: Mapped[UUIDStrPK]

    first_name: Mapped[str_256 | None]
    last_name: Mapped[str_256 | None]
    email: Mapped[str_256] = mapped_column(unique=True)
    password: Mapped[str_128 | None]
    last_login: Mapped[datetime | None]
    last_password_change: Mapped[datetime | None]

    modified: Mapped[datetime | None] = mapped_column()

    # the groups this user is part of
    groups: Mapped[list[Group]] = relationship(
        'Group',
        secondary=user_group_association,
        back_populates='users',
    )

    meetings: Mapped[list['Meeting']] = relationship(
        'Meeting',
        secondary=meetings_users_association,
        back_populates='attendees',
    )

    # the groups this user is a leader of
    leading_groups: Mapped[list[WorkingGroup]] = relationship(
        'WorkingGroup',
        back_populates='leader',
    )

    statements = relationship(
        'Statement',
        back_populates='drafter',
        foreign_keys='[Statement.drafted_by]',  # todo: check this is needed
    )

    def __init__(
            self,
            email: str | None = None,
            first_name: str | None = None,
            last_name: str | None = None,
            groups: list[Group] | None = None,
    ):
        self.id = str(uuid.uuid4())
        self.email = email
        self.modified = datetime.now(timezone.utc)
        self.first_name = first_name
        self.last_name = last_name
        self.groups = groups or []

    def set_password(self, password: str) -> None:
        password = password or ''
        pwhash = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())
        self.password = pwhash.decode('utf8')
        self.last_password_change = datetime.now(timezone.utc)

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

    def __acl__(self) -> list['ACL']:
        """ Allow the profile to be viewed by logged-in users."""
        return [
            (Allow, Authenticated, ['view']),
        ]
