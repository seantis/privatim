from sqlalchemy import select
from wtforms import (StringField, validators, )

from wtforms.validators import InputRequired
from privatim.forms.core import Form

from privatim.forms.fields import TimezoneDateTimeField
from privatim.forms.fields import SearchableSelectField
from privatim.models import User, Meeting
from privatim.models import WorkingGroup
from privatim.i18n import _


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from wtforms import Field


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

    name = StringField(label=_('Name'), validators=[InputRequired()])

    time = TimezoneDateTimeField(
        _('Time'),
        timezone='Europe/Zurich',
        validators=[InputRequired()],
    )

    attendees = SearchableSelectField(
        _('Attendees'),
        validators=[InputRequired()],
    )

    def validate_name(self, field: 'Field') -> None:
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
            else:
                field.populate_obj(obj, name)
