from sqlalchemy import select
from wtforms import validators
from wtforms.fields.choices import RadioField
from wtforms.fields.simple import TextAreaField
from wtforms.validators import ValidationError

from privatim.forms.core import Form
from privatim.i18n import _
from privatim.models import Meeting


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.models import AgendaItem


class AgendaItemForm(Form):

    def __init__(
        self,
        context: 'Meeting | AgendaItem',
        request: 'IRequest',
    ) -> None:

        self._title = (
            _('Add Agenda Item') if isinstance(context, Meeting) else
            _('Edit Agenda Item')
        )

        super().__init__(
            request.POST,
            obj=context,
            meta={'context': context, 'request': request},
        )

    title = TextAreaField(
        label=_('Title'), validators=[validators.DataRequired()],
        render_kw={'rows': 3}
    )
    description = TextAreaField(_('Description'), render_kw={'rows': 5})

    def populate_obj(self, obj: 'AgendaItem') -> None:  # type:ignore[override]
        super().populate_obj(obj)
        for name, field in self._fields.items():
            field.populate_obj(obj, name)


class AgendaItemCopyForm(Form):

    def __init__(
        self,
        context: Meeting,
        request: 'IRequest',
    ) -> None:

        self._title = _('Select Destionation for Agenda Item')

        super().__init__(
            request.POST,
            obj=context,
            meta={'context': context, 'request': request},
        )

        all_meetings_for_choices = [
            (str(meeting.id), meeting.name)
            # valid destination are all meetings except the one from which
            # we are copying from
            for meeting in request.dbsession.execute(
                select(Meeting).where(Meeting.id != context.id)
            ).scalars().all()
        ]
        if not all_meetings_for_choices:
            self.copy_to.validators.append(
                lambda form, field: ValidationError(
                    _('No valid destination meetings available.')
                )
            )
        self.copy_to.choices = all_meetings_for_choices

    copy_to = RadioField(
        label=_('Copy to'), validators=[validators.DataRequired()]
    )

    def populate_obj(self, obj: 'AgendaItem') -> None:  # type:ignore[override]
        super().populate_obj(obj)
        for name, field in self._fields.items():
            field.populate_obj(obj, name)
