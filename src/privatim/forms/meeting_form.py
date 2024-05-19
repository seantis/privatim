from sqlalchemy import select
from wtforms import (
    StringField,
    validators,
)

from privatim.forms.core import Form

from privatim.forms.fields import TimezoneDateTimeField  # type: ignore
from privatim.forms.fields import SearchableSelectField  # type: ignore
from privatim.models import User, Meeting
from privatim.i18n import _

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.models import WorkingGroup


class MeetingForm(Form):

    def __init__(
            self,
            context: 'WorkingGroup | Meeting',
            request: 'IRequest',
            prefix:  str = 'edit-xhr'
    ) -> None:

        self.title = (
            _('Add Meeting') if context is None else
            _('Edit meeting')
        )

        session = request.dbsession
        super().__init__(
            request.POST,
            obj=context,
            prefix=prefix,
            meta={
                'context': context,
                'dbsession': session
            }
        )

        users = session.execute(select(User)).scalars().all()
        self.attendees.choices = [(str(u.id), u.fullname) for u in users]

    name = StringField(label=_('Name'), validators=[validators.DataRequired()])

    time = TimezoneDateTimeField(
        _('Time'),
        format='%Y-%m-%dT%H:%M',
        # default=utcnow,
        validators=[validators.InputRequired()],
        timezone='Europe/Zurich',
    )
    attendees = SearchableSelectField(
        'Attendees',
        validators=[validators.InputRequired()],
    )

    def populate_obj(self, obj: Meeting) -> None:
        for name, field in self._fields.items():
            if isinstance(field, SearchableSelectField):
                session = self.meta.dbsession
                stmt = select(User).where(User.id.in_(field.raw_data))
                attendees = session.execute(stmt).scalars().all()
                obj.attendees = attendees
            else:
                field.populate_obj(obj, name)
