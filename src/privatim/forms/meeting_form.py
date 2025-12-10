from __future__ import annotations
from typing import TYPE_CHECKING, Any, NamedTuple

from sqlalchemy import select
from wtforms import StringField, validators
from wtforms.fields.form import FormField
from wtforms.fields.list import FieldList
from wtforms.fields.simple import BooleanField
from wtforms.validators import InputRequired

from privatim.forms.common import DEFAULT_UPLOAD_LIMIT
from privatim.forms.core import Form
from privatim.forms.fields import (
    TimezoneDateTimeField,
    ConstantTextAreaField,
    UploadMultipleFilesWithORMSupport,
    SearchableMultiSelectField
)
from privatim.forms.validators import FileExtensionsAllowed, FileSizeLimit
from privatim.i18n import _
from privatim.models import Meeting, MeetingUserAttendance, User, WorkingGroup
from privatim.models.association_tables import AttendanceStatus
from privatim.models.file import SearchableFile
from privatim.utils import get_guest_and_removed_users, status_is_checked


if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pyramid.interfaces import IRequest
    from sqlalchemy.orm import Session
    from webob.multidict import GetDict
    from wtforms import Field
    from wtforms.meta import _MultiDictLike


class CheckboxField(BooleanField):
    pass


class AttendanceForm(Form):
    user_id = StringField(
        'user_id',
        render_kw={'class': 'hidden no-white-background'},
    )
    fullname = StringField(
        _('Name'),
        render_kw={'disabled': 'disabled', 'class': 'no-white-background'},
    )
    status = CheckboxField(
        _('Attended'),
        render_kw={'class': 'no-white-background'},
        default=False
    )
    remove = CheckboxField(
        _('Remove'),
        render_kw={'class': 'no-white-background'},
        default=False
    )


class MeetingForm(Form):

    def __init__(
            self,
            context: WorkingGroup | Meeting,
            request: IRequest,
    ) -> None:

        self._title = (
            _('Add Meeting') if isinstance(context, WorkingGroup) else
            _('Edit meeting')
        )
        assert isinstance(context, (Meeting, WorkingGroup))
        self.context = context

        session = request.dbsession
        super().__init__(
            request.POST if request.POST else None,
            obj=context,
            meta={
                'context': context,
                'dbsession': session,
                'request': request
            }
        )
        guest_users, removed_users = get_guest_and_removed_users(
            session, context)
        self.attendees.choices = [
            (str(u.id), f'{u.first_name} {u.last_name}')
            for u in guest_users | removed_users
        ]

    name: ConstantTextAreaField = ConstantTextAreaField(
        label=_('Name'), validators=[InputRequired()]
    )

    time: TimezoneDateTimeField = TimezoneDateTimeField(
        label=_('Time'),
        timezone='Europe/Zurich',
        validators=[InputRequired()],
    )

    attendees: SearchableMultiSelectField = SearchableMultiSelectField(
        label=_('Guests (Members are added by default)'),
        validators=[validators.Optional()],
    )

    attendance = FieldList(
        FormField(AttendanceForm),
        label=_('Attendance'),
    )

    files = UploadMultipleFilesWithORMSupport(
        label=_('Documents'),
        validators=[
            validators.Optional(),
            FileExtensionsAllowed(['docx', 'doc', 'pdf', 'txt']),
            FileSizeLimit(DEFAULT_UPLOAD_LIMIT)
        ],
        file_class=SearchableFile
    )

    def validate_name(self, field: Field) -> None:
        if self._title == _('Add Meeting'):
            session = self.meta.dbsession
            if not field.data:
                return
            stmt = select(Meeting).where(Meeting.name == field.data)
            meeting = session.execute(stmt).scalar()
            if meeting:
                raise validators.ValidationError(_(
                    'A meeting with this name already exists.'
                ))

    def populate_obj(self, obj: Meeting) -> None:  # type:ignore[override]
        for name, field in self._fields.items():
            if isinstance(field, SearchableMultiSelectField):
                sync_meeting_attendance_records(
                    self,
                    obj,
                    self.meta.request.POST,
                    self.meta.dbsession,
                )
            elif name == 'attendance':
                # this is already handled in sync_meeting_attendance_records
                pass
            else:
                field.populate_obj(obj, name)

    def process(
        self,
        formdata: _MultiDictLike | None = None,
        obj: object | None = None,
        data: Mapping[str, Any] | None = None,
        extra_filters: Mapping[str, Sequence[Any]] | None = None,
        **kwargs: Any
    ) -> None:
        super().process(formdata, obj, **kwargs)
        if obj is None:
            return
        if not formdata:
            if isinstance(obj, Meeting):
                self.handle_process_edit(obj)
            else:
                self.handle_process_add(obj)  # type:ignore[arg-type]

    def handle_process_edit(self, obj: Meeting) -> None:
        self.attendance.entries = []
        records = obj.sorted_attendance_records
        for attendance_record in (
          self.meta.dbsession.execute(records).unique().scalars().all()
        ):
            status = (True
                      if attendance_record.status == AttendanceStatus.ATTENDED
                      else False)
            self.attendance.append_entry(
                {
                    'user_id': str(attendance_record.user_id),
                    'fullname': attendance_record.user.fullname_without_abbrev,
                    'status': status
                }
            )

    def handle_process_add(self, obj: WorkingGroup) -> None:
        assert isinstance(obj, WorkingGroup)
        # pre-fill the users with users of working group
        self.attendees.data = [e.id for e in obj.users]

        attendee_ids = self.attendees.data or []
        for attendee_id in attendee_ids:
            user = self.meta.dbsession.get(User, attendee_id)
            if user:
                self.attendance.append_entry(
                    {
                        'user_id': str(user.id),
                        'fullname': user.fullname,
                        'status': AttendanceStatus.INVITED,
                    }
                )


def sync_meeting_attendance_records(
    form: MeetingForm,
    obj: Meeting,
    post_data: GetDict,
    session: Session,
) -> None:
    """ Searches in request.POST to manually get data and find the status
    for each user and map it to MeetingUserAttendance."""

    class AttendanceValues(NamedTuple):
        is_present: bool
        should_remove: bool

    def find_attendance_in_form(user_id: str) -> AttendanceValues:
        """ Returns the values of the status and remove checkboxes, in that
        order """
        for f in form._fields.get('attendance', ()):  # type:ignore
            if f.user_id.data == user_id:
                # XXX this is kind of crude, but I couldn't find a way to do
                # it otherwise. Request.POST is somehow is not mapped to the
                # 'status' field in AttendanceForm.
                # We have to get it manually as a workaround
                return AttendanceValues(
                    is_present=status_is_checked(post_data, user_id),
                    should_remove=bool(f.remove.data)
                )
        return AttendanceValues(is_present=False, should_remove=False)

    assert isinstance(form.attendees, SearchableMultiSelectField)

    # Collect unique user IDs from attendees and attendance entries
    entries = form.attendance.entries
    attendance_user_ids = {entry.data['user_id'] for entry in entries}
    attendee_ids = set(form.attendees.data or [])

    # Merge both sets of user IDs
    all_user_ids = attendance_user_ids | attendee_ids
    stmt = select(User).where(User.id.in_(all_user_ids))
    users_for_edited_meeting = session.execute(stmt).scalars().all()

    obj.attendance_records = []
    for user in users_for_edited_meeting:
        attended, remove = find_attendance_in_form(user.id)
        if not remove:  # Only add if not marked for removal
            obj.attendance_records.append(MeetingUserAttendance(
                meeting=obj,
                user=user,
                status=AttendanceStatus.ATTENDED
                if attended else AttendanceStatus.INVITED,
            ))
