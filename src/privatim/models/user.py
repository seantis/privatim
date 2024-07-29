import uuid
from functools import cached_property
from pyramid.authorization import Allow
from pyramid.authorization import Authenticated
import bcrypt
from datetime import datetime
from datetime import timezone

from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm.session import object_session
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey, select

from privatim.models import Group, WorkingGroup
from privatim.models.profile_pic import get_or_create_default_profile_pic
from privatim.orm.meta import UUIDStr as UUIDStrType
from privatim.models.group import user_group_association
from privatim.orm import Base
from privatim.orm.meta import UUIDStrPK, str_256, str_128


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from privatim.models.association_tables import MeetingUserAttendance
    from privatim.types import ACL
    from privatim.models import Meeting
    from sqlalchemy import Select
    from privatim.models.commentable import Comment
    from privatim.models import Consultation
    from privatim.models import GeneralFile


class User(Base):
    __tablename__ = 'users'

    def __init__(
            self,
            email: str,
            first_name: str | None = None,
            last_name: str | None = None,
            groups: list[Group] | None = None,
    ):
        self.id = str(uuid.uuid4())
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.groups = groups or []

    id: Mapped[UUIDStrPK]

    first_name: Mapped[str_256 | None]
    last_name: Mapped[str_256 | None]
    email: Mapped[str_256] = mapped_column(unique=True)
    password: Mapped[str_128 | None]
    last_login: Mapped[datetime | None]
    last_password_change: Mapped[datetime | None]

    profile_pic_id: Mapped[UUIDStrType | None] = mapped_column(
        ForeignKey('general_files.id', ondelete='SET NULL'),
        nullable=True
    )
    profile_pic: Mapped['GeneralFile | None'] = relationship(
        'GeneralFile',
        single_parent=True,
        passive_deletes=True,
        cascade='all, delete-orphan'
    )

    # the function of the user in the organization
    function: Mapped[str | None]

    modified: Mapped[datetime | None] = mapped_column()

    # the groups this user is part of
    groups: Mapped[list[Group]] = relationship(
        'Group',
        secondary=user_group_association,
        back_populates='users',
    )

    meeting_attendance: Mapped[list['MeetingUserAttendance']] = relationship(
        'MeetingUserAttendance',
        back_populates='user',
        cascade='all, delete-orphan'
    )

    @hybrid_property
    def meetings(self) -> list['Meeting']:
        return [record.meeting for record in self.meeting_attendance]

    @meetings.expression  # type: ignore[no-redef]
    def meetings(cls) -> 'Select[tuple[Meeting]]':
        from privatim.models.meeting import Meeting
        from privatim.models.association_tables import MeetingUserAttendance
        return (
            select(Meeting)
            .join(MeetingUserAttendance)
            .filter(MeetingUserAttendance.user_id == cls.id)
        )

    # the groups this user is a leader of
    leading_groups: Mapped[list[WorkingGroup]] = relationship(
        'WorkingGroup',
        back_populates='leader',
    )

    comments: Mapped[list['Comment']] = relationship(
        'Comment', back_populates='user',
    )

    consultations: Mapped[list['Consultation']] = relationship(
        'Consultation',
        back_populates='creator',
        foreign_keys='Consultation.creator_id',
    )

    created_meetings: Mapped[list['Consultation']] = relationship(
        'Meeting',
        back_populates='creator',
        foreign_keys='Meeting.creator_id',
    )

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

    @property
    def picture(self) -> 'GeneralFile':
        """ Returns the user's profile picture or the default picture. """
        session = object_session(self)
        assert session is not None
        if self.profile_pic:
            return self.profile_pic
        else:
            return get_or_create_default_profile_pic(session)

    def __acl__(self) -> list['ACL']:
        """ Allow the profile to be viewed by logged-in users."""
        return [
            (Allow, Authenticated, ['view']),
        ]

    def __repr__(self) -> str:
        return f'<User {self.fullname}>'
