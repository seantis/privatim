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

        query = select(User).options(
            load_only(User.id, User.first_name, User.last_name)
        )
        users = session.execute(query).scalars().all()
        self.attendees.choices = [(str(u.id), u.fullname) for u in users]

    name: ConstantTextAreaField = ConstantTextAreaField(
        label=_('Name'), validators=[InputRequired()]
    )

    time: TimezoneDateTimeField = TimezoneDateTimeField(
        label=_('Time'),
        timezone='Europe/Zurich',
        validators=[InputRequired()],
    )

    attendees: SearchableMultiSelectField = SearchableMultiSelectField(
        label=_('Members'),
        validators=[InputRequired()],
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
                # this is already handled in SearchableMultiSelectField above
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
        if isinstance(obj, Meeting):
            self.handle_process_edit(obj)
        else:
            if obj is not None:
                self.handle_process_add(obj)  # type:ignore[arg-type]

    def handle_process_edit(self, obj: Meeting) -> None:
        if obj and hasattr(obj, 'attendees'):
            self.attendees.data = [str(user.id) for user in obj.attendees]

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
        # pre-fill the users with users of working group

        assert isinstance(obj, WorkingGroup)
        self.attendees.data = [e.id for e in obj.users]

        attendee_ids = self.attendees.data or []
        for attendee_id in attendee_ids:
            user = self.meta.dbsession.get(User, attendee_id)
            if user:
                self.attendance.append_entry(
                    {'user_id': str(user.id), 'fullname': user.fullname,
                        'status': AttendanceStatus.INVITED, })


def sync_meeting_attendance_records(
    meeting_form: MeetingForm,
    obj: Meeting,
    post_data: 'GetDict',
    session: 'Session',
) -> None:
    """ Searches in request.POST to manually get data and find the status
    for each user and map it to MeetingUserAttendance."""

    def find_attendance_in_form(user_id: str) -> bool:
        for f in meeting_form._fields.get('attendance', ()):  # type:ignore
            if f.user_id.data == user_id:
                # XXX this is kind of crude, but I couldn't find a way to do
                # it otherwise. Request.POST is somehow is not mapped to the
                # 'status' field in AttendanceForm.
                # We have to get it manually as a workaround
                return attendance_status(post_data, user_id)

        return False

    assert isinstance(meeting_form.attendees, SearchableMultiSelectField)
    stmt = select(User).where(User.id.in_(
        # FIXME: Does this give the correct result for an empty selection?
        meeting_form.attendees.raw_data or ()
    ))
    users = session.execute(stmt).scalars().all()
    # Clear existing attendance records
    obj.attendance_records = []
    # Create new attendance records
    for user in users:
        actual_status = AttendanceStatus.INVITED
        if find_attendance_in_form(user.id) is True:
            actual_status = AttendanceStatus.ATTENDED
        attendance = MeetingUserAttendance(
            meeting=obj, user=user, status=actual_status
        )
        obj.attendance_records.append(attendance)
