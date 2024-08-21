import uuid
from functools import cached_property
from random import choice

from sedate import utcnow

from privatim.pyavatar import PyAvatar
from pyramid.authorization import Allow
from pyramid.authorization import Authenticated
import bcrypt
from datetime import datetime
from datetime import timezone

from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm.session import object_session
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey, select
from sqlalchemy.orm import Mapped

from privatim.forms.constants import AVATAR_COLORS
from privatim.models import Group, WorkingGroup
from privatim.models.profile_pic import get_or_create_default_profile_pic
from privatim.orm.meta import UUIDStr as UUIDStrType
from privatim.models.group import user_group_association
from privatim.orm import Base
from privatim.orm.meta import UUIDStrPK, str_256, str_128, str_32
from privatim.models.file import GeneralFile


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from privatim.models.association_tables import MeetingUserAttendance
    from privatim.types import ACL
    from sqlalchemy.orm import Session
    from pyramid.interfaces import IRequest
    from privatim.models import Meeting
    from sqlalchemy import ScalarSelect
    from privatim.models.comment import Comment
    from privatim.models import Consultation


class User(Base):
    __tablename__ = 'users'

    def __init__(
            self,
            email: str,
            first_name: str = '',
            last_name: str = '',
            abbrev: str = '',
            groups: list[Group] | None = None,
    ):
        self.id = str(uuid.uuid4())
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.groups = groups or []
        self.abbrev = abbrev

        if abbrev:
            self.abbrev = abbrev
        else:
            self.abbrev = self.generate_default_abbreviation()

    id: Mapped[UUIDStrPK]

    first_name: Mapped[str_256]
    last_name: Mapped[str_256]
    email: Mapped[str_256] = mapped_column(unique=True)
    locale: Mapped[str_32 | None]
    password: Mapped[str_128 | None]
    mobile_number: Mapped[str_128 | None] = mapped_column(unique=True)
    last_login: Mapped[datetime | None]
    last_password_change: Mapped[datetime | None]
    abbrev: Mapped[str_32]

    profile_pic_id: Mapped[UUIDStrType | None] = mapped_column(
        ForeignKey('general_files.id', ondelete='SET NULL'),
        nullable=True
    )
    profile_pic: Mapped[GeneralFile | None] = relationship(
        GeneralFile,
        single_parent=True,
        passive_deletes=True,
        cascade='all, delete-orphan'
    )

    def generate_default_abbreviation(self) -> str:
        initials = []
        if self.first_name:
            initials.append(self.first_name[0].upper())
        if self.last_name:
            initials.append(self.last_name[0].upper())
        return ''.join(initials) if initials else ''

    def generate_profile_picture(self, session: 'Session') -> None:
        """
        Generate a profile picture based on user initials.
        If no name is provided, use the first letter of the email.
        Uses a predefined color palette for the background.
        """
        # Choose a random color from the palette
        bg_color = choice(AVATAR_COLORS)  # nosec[B311]
        avatar = PyAvatar(
            self.abbrev, size=250, char_spacing=35, color=bg_color,
        )
        general_file = GeneralFile(
            filename=f'{self.id}_avatar.png',
            content=avatar.stream()
        )
        session.add(general_file)
        session.flush()  # Flush to get the ID assigned
        self.profile_pic = general_file

    def profile_pic_download_link(self, request: 'IRequest') -> str:
        return (
            request.route_url('download_file', id=self.profile_pic_id)
            if (self.profile_pic_id)
            else request.static_url('privatim:static/default_profile_icon.png')
        )

    created: Mapped[datetime] = mapped_column(default=utcnow)
    updated: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    # the groups this user is part of
    groups: Mapped[list[Group]] = relationship(
        'Group',
        secondary=user_group_association,
        back_populates='users',
    )

    leading_groups: Mapped[list[WorkingGroup]] = relationship(
        'WorkingGroup',
        back_populates='leader',
        foreign_keys='WorkingGroup.leader_id'
    )

    chaired_groups: Mapped[list[WorkingGroup]] = relationship(
        'WorkingGroup',
        back_populates='chairman',
        foreign_keys='WorkingGroup.chairman_id'
    )

    meeting_attendance: Mapped[list['MeetingUserAttendance']] = relationship(
        'MeetingUserAttendance',
        back_populates='user',
        cascade='all, delete-orphan'
    )

    @hybrid_property
    def meetings(self) -> list['Meeting']:
        return [record.meeting for record in self.meeting_attendance]

    @meetings.inplace.expression
    @classmethod
    def _meetings_expression(cls) -> 'ScalarSelect[Meeting]':
        from privatim.models.meeting import Meeting
        from privatim.models.association_tables import MeetingUserAttendance
        return (
            select(Meeting)
            .join(MeetingUserAttendance)
            .filter(MeetingUserAttendance.user_id == cls.id)
            .scalar_subquery()
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
    def fullname_without_abbrev(self) -> str:
        parts = []
        if self.first_name:
            parts.append(self.first_name)
        if self.last_name:
            parts.append(self.last_name)
        if not parts:
            return self.email
        return ' '.join(parts)

    @cached_property
    def fullname(self) -> str:
        parts = []
        if self.first_name:
            parts.append(self.first_name)
        if self.last_name:
            parts.append(self.last_name)
        parts.append('(' + self.abbrev + ')')
        if not parts:
            return self.email
        return ' '.join(parts)

    @property
    def picture(self) -> GeneralFile:
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
