from datetime import datetime
from uuid import uuid4

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Enum
import bcrypt
from sedate import utcnow
from sqlalchemy import Table, Column, ForeignKey, String
from sqlalchemy.orm import Mapped, column_property
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from privatim.orm import Base
from privatim.orm.meta import UUIDStrPK, str_256, str_128


from typing import TypeAlias, Literal, TYPE_CHECKING
if TYPE_CHECKING:
    PersonType: TypeAlias = Literal['internal', 'external']


PERSON_TYPES: tuple['PersonType', ...] = ('internal', 'external')

person_group_association = Table(
    'person_group_association',
    Base.metadata,
    Column(
        'group_id',
        UUID(as_uuid=True),
        ForeignKey('group.id'),
        primary_key=True,
    ),
    Column(
        'person_id',
        UUID(as_uuid=True),
        ForeignKey('person.id'),
        primary_key=True,
    ),
)


class Group(Base):
    """A group of users."""

    __tablename__ = "group"

    id: Mapped[UUIDStrPK]

    name: Mapped[str] = mapped_column(String, nullable=False)

    description: Mapped[str] = Column(String)

    # Connects to Person through the association table
    members = relationship(
        "Person",
        secondary=person_group_association,
        back_populates="groups",  # Corrected to 'groups'
    )

    # leader_id = mapped_column(UUIDStr, ForeignKey("user.id"), unique=True)
    # leader = relationship("User",
    # back_populates="leading_group",
    # uselist=False)



class Person(Base):

    __tablename__ = "person"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    type = Column(
        Enum(*PERSON_TYPES), name='person_type', nullable=False, default='internal')

    __mapper_args__ = {
        "polymorphic_on": type,
        "polymorphic_identity": 'external',
    }

    first_name: Mapped[str_256 | None]
    last_name: Mapped[str_256 | None]

    # the groups this person is a member of
    # Correctly connects back to the Group's 'members' relationship
    groups = relationship(
        "Group",
        secondary=person_group_association,
        back_populates="members",
    )

    def __repr__(self):
        return f"<Person(id={self.id}, type={self.type}>"


class User(Person):
    __tablename__ = "user"

    __mapper_args__ = {
        "polymorphic_identity": 'internal',
    }

    id = Column(UUID(as_uuid=True), ForeignKey('person.id'), primary_key=True)

    email: Mapped[str_256] = mapped_column(unique=True)

    password: Mapped[str_128 | None]

    last_login: Mapped[datetime | None]
    last_password_change: Mapped[datetime | None]

    created: Mapped[datetime] = mapped_column(default=utcnow)
    modified: Mapped[datetime | None] = mapped_column(onupdate=utcnow)

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


class Participant(Person):
    """Represents a non-registered individual.
    This exists to decouple from `User`, as a user account might not always be
    desirable (e.g. for associated people). """


    __tablename__ = "participant"

    id = Column(UUID(as_uuid=True), ForeignKey('person.id'), primary_key=True)

    __mapper_args__ = {
        "polymorphic_identity": 'external',
    }

    def __repr__(self):
        return f"<Guest(id={self.id}, email={self.email})>"