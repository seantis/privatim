from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import load_only
from wtforms import StringField, validators
from wtforms.fields.form import FormField
from wtforms.fields.list import FieldList
from wtforms.fields.simple import BooleanField
from wtforms.validators import InputRequired

from privatim.forms.core import Form

from privatim.forms.fields import TimezoneDateTimeField
from privatim.forms.fields.fields import SearchableMultiSelectField, \
    ConstantTextAreaField
from privatim.models import User, Meeting
from privatim.models import WorkingGroup
from privatim.i18n import _
from privatim.models.association_tables import AttendanceStatus
from privatim.models import MeetingUserAttendance

from typing import TYPE_CHECKING, Any

from privatim.utils import attendance_status
if TYPE_CHECKING:
    from wtforms import Field
    from pyramid.interfaces import IRequest
    from webob.multidict import GetDict
    from sqlalchemy.orm import Session
    from wtforms.meta import _MultiDictLike
    from collections.abc import Mapping, Sequence


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


class MeetingForm(Form):

    def __init__(
            self,
            context: WorkingGroup | Meeting,
            request: 'IRequest',
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
        group_id_condition = (
            UUID(context.working_group.id)
            if isinstance(context, Meeting)
            else UUID(context.id)
        )
        guest_users = (
            session.execute(
                select(User)
                .options(load_only(User.id, User.first_name, User.last_name))
                .filter(
                    ~User.groups.any(WorkingGroup.id == group_id_condition)
                )
            )
            .scalars()
            .all()
        )
        self.attendees.choices = [
            (str(u.id), f"{u.first_name} {u.last_name}") for u in guest_users
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

    def validate_name(self, field: 'Field') -> None:
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
        formdata: '_MultiDictLike | None' = None,
        obj: object | None = None,
        data: 'Mapping[str, Any] | None' = None,
        extra_filters: 'Mapping[str, Sequence[Any]] | None' = None,
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
                    'fullname': attendance_record.user.fullname,
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
    post_data: 'GetDict',
    session: 'Session',
) -> None:
    """ Searches in request.POST to manually get data and find the status
    for each user and map it to MeetingUserAttendance."""

    def find_attendance_in_form(user_id: str) -> bool:
        for f in form._fields.get('attendance', ()):  # type:ignore
            if f.user_id.data == user_id:
                # XXX this is kind of crude, but I couldn't find a way to do
                # it otherwise. Request.POST is somehow is not mapped to the
                # 'status' field in AttendanceForm.
                # We have to get it manually as a workaround
                return attendance_status(post_data, user_id)

        return False

    assert isinstance(form.attendees, SearchableMultiSelectField)

    # Extract user IDs and statuses from the attendance FieldList
    attendance_data = {
        entry.data['user_id']: entry.data['status']
        for entry in form.attendance.entries
    }
    # Get user IDs from the attendees field
    attendee_ids = set(form.attendees.data or [])

    # Combine user IDs from attendance and attendees, removing duplicates
    all_user_ids = set(attendance_data.keys()) | attendee_ids

    stmt = select(User).where(User.id.in_(all_user_ids))
    users_for_edited_meeting = session.execute(stmt).scalars().all()
    obj.attendance_records = []
    for user in users_for_edited_meeting:
        actual_status = AttendanceStatus.INVITED
        if find_attendance_in_form(user.id) is True:
            actual_status = AttendanceStatus.ATTENDED
        attendance = MeetingUserAttendance(
            meeting=obj, user=user, status=actual_status
        )
        obj.attendance_records.append(attendance)
