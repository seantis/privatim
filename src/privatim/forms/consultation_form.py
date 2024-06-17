from privatim.forms.constants import CANTONS_SHORT
from privatim.forms.core import Form
from wtforms import StringField
from wtforms.fields.choices import SelectField
from wtforms.fields.simple import TextAreaField
from wtforms.validators import DataRequired
from wtforms import validators

from privatim.forms.fields import UploadMultipleField, SearchableSelectField
from privatim.i18n import _, translate

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.models import Consultation


STATUS_CHOICES = [
    (code, label) for code, label in [
        ('1', _('Open')),
        ('2', _('Closed')),
        ('3', _('In Progress')),
    ]
]


class ConsultationForm(Form):
    def __init__(
        self, context: 'Consultation | None', request: 'IRequest'
    ) -> None:
        self._title = _('Edit Consultation')
        super().__init__(
            request.POST,
            obj=context,
            meta={'context': context, 'request': request},
        )
        translated_choices = [
            (code, translate(label))
            for code, label in STATUS_CHOICES
        ]
        self.status.choices = translated_choices

    title = StringField(
        _('Title'),
        validators=[DataRequired()],
    )
    description = TextAreaField(_('Description'))
    recommendation = StringField(_('Recommendation'))
    status = SelectField(
        _('Status'),
        choices=[]
    )
    cantons = SearchableSelectField(
        _('Cantons'),
        choices=[('', '')] + CANTONS_SHORT,
        validators=[
            validators.Optional(),
        ],
    )
    documents = UploadMultipleField(
        label=_('Documents'),
        validators=[
            validators.Optional(),
        ]
    )
