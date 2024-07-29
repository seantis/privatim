from sqlalchemy import select
from sqlalchemy.orm import load_only
from wtforms import (StringField, validators, )
from wtforms.fields.form import FormField
from wtforms.fields.list import FieldList
from wtforms.fields.simple import BooleanField
from wtforms.validators import InputRequired

from privatim.forms.core import Form

from privatim.forms.fields import TimezoneDateTimeField
from privatim.forms.fields.fields import SearchableSelectField
from privatim.models import User, Meeting
from privatim.models import WorkingGroup
from privatim.i18n import _
from privatim.models.association_tables import AttendanceStatus
from privatim.models import MeetingUserAttendance


from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from wtforms import Field
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

        session = request.dbsession
        super().__init__(
            request.POST,
            obj=context,
            meta={
                'context': context,
                'dbsession': session
            }
        )

        query = select(User).options(
            load_only(User.id, User.first_name, User.last_name)
        )
        users = session.execute(query).scalars().all()
        self.attendees.choices = [(str(u.id), u.fullname) for u in users]

    name: StringField = StringField(
        label=_('Name'), validators=[InputRequired()]
    )

    time: TimezoneDateTimeField = TimezoneDateTimeField(
        label=_('Time'),
        timezone='Europe/Zurich',
        validators=[InputRequired()],
    )

    attendees: SearchableSelectField = SearchableSelectField(
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
            if isinstance(field, SearchableSelectField):
                pass
                # session = self.meta.dbsession
                # stmt = select(User).where(User.id.in_(field.raw_data))
                # users = session.execute(stmt).scalars().all()
                #
                # # Clear existing attendance records
                # obj.attendance_records = []
                #
                # # Create new attendance records
                # for user in users:
                #     attendance = MeetingUserAttendance(
                #         meeting=obj, user=user, status=AttendanceStatus.INVITED
                #     )
                #     obj.attendance_records.append(attendance)
            # elif name == 'attendance':
            #     for status_form in field:
            #         user_id = status_form.user_id.data
            #         attended = status_form.status.data
            #         attendance_record = next(
            #             (
            #                 ar for ar in obj.attendance_records
            #                 if str(ar.user_id) == user_id
            #             ),
            #             None,
            #         )
            #         if attendance_record:
            #             attendance_record.status = (
            #                 AttendanceStatus.ATTENDED
            #                 if attended
            #                 else AttendanceStatus.INVITED
            #             )
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
            self.attendance.entries = []
            for attendance_record in obj.attendance_records:
                self.attendance.append_entry(
                    {
                        'user_id': str(attendance_record.user_id),
                        'fullname': attendance_record.user.fullname,
                        'status': attendance_record.status,
                    }
                )
        else:
            if obj is None:
                # This is erroneously set because WorkingGroup also has name
                self.name.data = ''

            self.attendance.entries = []
            if formdata is None:
                return

            attendee_ids = self.attendees.data or []
            session = self.meta.dbsession

            for attendee_id in attendee_ids:
                user = session.get(User, attendee_id)
                if user:
                    self.attendance.append_entry({
                        'user_id': str(user.id),
                        'fullname': user.fullname,
                        'status': AttendanceStatus.INVITED,
                    })
