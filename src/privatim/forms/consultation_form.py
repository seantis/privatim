from wtforms import Form, StringField
from wtforms.fields.simple import TextAreaField
from wtforms.validators import DataRequired
from privatim.i18n import _

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.models import Consultation


class ConsultationForm(Form):

    def __init__(
        self, context: 'Consultation | None', request: 'IRequest'
    ) -> None:
        self.title = _('Edit Consultation')

        super().__init__(
            request.POST,
            obj=context,
            meta={'context': context, 'request': request},
        )

    title = StringField(_('Title'),
                        validators=[DataRequired()],
                        default='test')

    description = TextAreaField(_('Description'), default='test')
    comments = TextAreaField(_('Comments'), default='test')
    recommendation = StringField(_('Recommendation'), default='test')
    status = StringField(_('Status'), default='test')
