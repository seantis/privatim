from datetime import datetime

import bcrypt
from sedate import utcnow
from sqlalchemy import Table, Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from privatim.orm import Base
from privatim.orm.meta import UUIDStrPK, Text

# Association table for many-to-many relationship between WorkGroup and User
user_workgroup_association = Table(
    "user_workgroup",
    Base.metadata,
    Column(
        "user_id", UUID(as_uuid=True), ForeignKey("user.id"),
        primary_key=True
    ),
    Column(
        "workgroup_id",
        UUID(as_uuid=True),
        ForeignKey("working_group.id"),
        primary_key=True,
    ),
)


class WorkGroup(Base):
    """Arbeitsgruppe"""

    __tablename__ = "working_group"

    id: Mapped[UUIDStrPK] = mapped_column()

    name = Column(String, nullable=False)

    description = Column(String)

    # working group but should work for many to many
    members = relationship(
        "User",
        secondary=user_workgroup_association,
        back_populates="working_groups",
    )

    # leader_id = mapped_column(UUIDStr, ForeignKey("user.id"), unique=True)
    # leader = relationship("User",
    # back_populates="leading_group",
    # uselist=False)


class User(Base):
    __tablename__ = "user"

    id: Mapped[UUIDStrPK] = mapped_column()

    # the working group this user belongs to
    working_groups = relationship(
        "WorkGroup",
        secondary=user_workgroup_association,
        back_populates="members",
    )

    first_name: Mapped[Text | None] = mapped_column(default=None)

    last_name: Mapped[Text | None] = mapped_column(default=None)

    email: Mapped[Text | None] = mapped_column(
        default=None, unique=True, nullable=False
    )

    password: Mapped[Text | None] = mapped_column(default=None)

    mobile_number: Mapped[Text | None] = mapped_column(default=None)

    modified: Mapped[datetime | None] = mapped_column(default=None)

    last_login: Mapped[datetime | None] = mapped_column(default=None)

    last_password_change: Mapped[datetime | None] = mapped_column(default=None)

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
