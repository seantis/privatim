from wtforms import StringField
from wtforms import validators
from wtforms.fields.simple import TextAreaField

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

    title = StringField(
        label=_('Title'), validators=[validators.DataRequired()]
    )
    description = TextAreaField(_('Description'))

    def populate_obj(self, obj: 'AgendaItem') -> None:  # type:ignore[override]
        super().populate_obj(obj)
        for name, field in self._fields.items():
            field.populate_obj(obj, name)
