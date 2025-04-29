from privatim.forms.common import DEFAULT_UPLOAD_LIMIT
from privatim.forms.constants import CANTONS_SHORT
from privatim.forms.core import Form
from wtforms.fields.choices import SelectField
from wtforms.fields.simple import TextAreaField
from wtforms.validators import DataRequired
from wtforms import validators

from privatim.forms.fields.fields import (
    UploadMultipleFilesWithORMSupport,
    SearchableMultiSelectField,
    ConstantTextAreaField,
)
from privatim.forms.validators import FileSizeLimit, FileExtensionsAllowed
from privatim.i18n import _
from privatim.models import SearchableFile


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.models import Consultation


STATUS_CHOICES = [
    ('Created', _('Created')),
    ('Closed', _('Closed')),
    ('In Progress', _('In Progress')),
    ('Waiving', _('Waiving')),
]


class ConsultationForm(Form):
    def __init__(
        self, context: 'Consultation | None', request: 'IRequest'
    ) -> None:
        self._title = _('Edit Consultation')
        session = request.dbsession
        super().__init__(
            request.POST if request.POST else None,
            obj=context,
            meta={
                'context': context,
                'dbsession': session
            }
        )

        self.status.choices = STATUS_CHOICES

    title = ConstantTextAreaField(
        _('Title'),
        validators=[DataRequired()],
    )

    description = TextAreaField(
        _('Description'),
        render_kw={'rows': 6},
    )

    recommendation = TextAreaField(
        _('Recommendation'),
        render_kw={'rows': 6},
    )
    evaluation_result = TextAreaField(
        _('Evaluation Result'),
        render_kw={'rows': 6},
    )

    decision = TextAreaField(
        _('Decision'),
        render_kw={'rows': 6},
    )

    status = SelectField(
        _('Status'),
        choices=[],  # We'll set this in __init__
    )
    secondary_tags = SearchableMultiSelectField(
        _('Cantons'),
        choices=[('', '')] + CANTONS_SHORT,
        validators=[
            validators.Optional(),
        ],
    )

    files = UploadMultipleFilesWithORMSupport(
        label=_('Documents'),
        validators=[
            validators.Optional(),
            FileExtensionsAllowed(['docx', 'doc', 'pdf', 'txt']),
            FileSizeLimit(DEFAULT_UPLOAD_LIMIT)
        ],
        file_class=SearchableFile
    )
