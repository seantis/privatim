from sqlalchemy import select
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


from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from wtforms import Field
    from wtforms.meta import _MultiDictLike
    from collections.abc import Mapping, Sequence


class CheckboxField(BooleanField):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)


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

        users = session.execute(select(User)).scalars().all()
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
            stmt = select(Meeting).where(Meeting.name == field.data)
            meeting = session.execute(stmt).scalar()
            if meeting:
                raise validators.ValidationError(_(
                    'A meeting with this name already exists.'
                ))

    def populate_obj(self, obj: Meeting) -> None:  # type:ignore[override]
        for name, field in self._fields.items():
            if isinstance(field, SearchableSelectField):
                session = self.meta.dbsession
                stmt = select(User).where(User.id.in_(field.raw_data))
                attendees = session.execute(stmt).scalars().all()
                obj.attendees = attendees
            elif name == 'attendance':
                for status_form in field:
                    user_id = status_form.user_id.data
                    status = status_form.status.data
                    potential_attendee = next(
                        (p for p in obj.attendees if str(p.id) == user_id
                         and status is True), None
                    )
                    if potential_attendee:
                        obj.attended_attendees.append(potential_attendee)
            else:
                field.populate_obj(obj, name)

    def process(
        self,
        formdata: '_MultiDictLike | None' = None,
        obj:           object | None = None,
        data:          'Mapping[str, Any] | None' = None,
        extra_filters: 'Mapping[str, Sequence[Any]] | None' = None,
        **kwargs: Any
    ) -> None:

        # todo: test this
        super().process(formdata, obj, **kwargs)
        if isinstance(obj, Meeting):
            self.attendance.entries = []

            # A set for O(1) lookup
            attended_set = set(obj.attended_attendees)

            for attendee in obj.attendees:
                self.attendance.append_entry(
                    {
                        'user_id': str(attendee.id),
                        'fullname': attendee.fullname,
                        'status': (
                            'attended'
                            if attendee in attended_set
                            else 'invited'
                        ),
                    }
                )
        else:
            self.attendance.entries = []
            if formdata:
                attendee_ids = (self.attendees.data
                                if self.attendees.data else [])
                session = self.meta['dbsession']
                for attendee_id in attendee_ids:
                    user = session.get(User, attendee_id)
                    if user:
                        self.attendance.append_entry(
                            {
                                'user_id': str(user.id),
                                'fullname': user.fullname,
                                'status': 'invited',
                            }
                        )
