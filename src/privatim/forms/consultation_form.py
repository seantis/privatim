from sqlalchemy import select

from privatim.forms.common import DEFAULT_UPLOAD_LIMIT
from privatim.forms.constants import CANTONS_SHORT
from privatim.forms.core import Form
from wtforms.fields.choices import SelectField
from wtforms.fields.simple import TextAreaField
from wtforms.validators import DataRequired
from wtforms import validators

from privatim.forms.fields.fields import (UploadMultipleFilesWithORMSupport,
                                          SearchableMultiSelectField,
                                          ConstantTextAreaField,
                                          )
from privatim.forms.validators import FileSizeLimit, FileExtensionsAllowed
from privatim.i18n import _, translate

from privatim.models import Tag, SearchableFile
from privatim.models.consultation import Status


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
        session = request.dbsession
        super().__init__(
            request.POST,
            obj=context,
            meta={
                'context': context,
                'dbsession': session
            }
        )

        self.status.choices = [
            (code, translate(label))
            for code, label in STATUS_CHOICES
        ]

    title = ConstantTextAreaField(
        _('Title'),
        validators=[DataRequired()],
    )

    # Beschreibung
    description = TextAreaField(
        _('Description'),
        render_kw={'rows': 6},
    )
    # Empfehlung
    recommendation = TextAreaField(
        _('Recommendation'),
        render_kw={'rows': 6},
    )

    # new Prüfergebnis
    evaluation_result = TextAreaField(
        _('Evaluation Result'),
        render_kw={'rows': 6},
    )

    # new: Beschluss
    decision = TextAreaField(
        _('Decision'),
        render_kw={'rows': 6},
    )

    status = SelectField(
        _('Status'),
        choices=[]
    )
    secondary_tags = SearchableMultiSelectField(
        _('Cantons'),
        choices=[('', '')] + CANTONS_SHORT,
        validators=[
            validators.Optional(),
        ],
        translations={
            'placeholder': translate(_('Choose a canton...')),
        }
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

    def populate_obj(
        self,
        obj: 'Consultation',  # type: ignore[override]
    ) -> None:
        session = self.meta.dbsession
        # todo: add files:
        for name, field in self._fields.items():
            if (
                isinstance(field, SearchableMultiSelectField)
                and field.raw_data is not None
            ):
                existing_tags = {
                    tag.name: tag
                    for tag in session.execute(
                        select(Tag).where(Tag.name.in_(field.raw_data))
                    )
                    .scalars()
                    .all()
                }
                # Create new tags for those not already existing
                new_tags = set()
                for tag_name in field.raw_data:
                    if tag_name not in existing_tags:
                        new_tag = Tag(name=tag_name)
                        session.add(new_tag)
                        new_tags.add(new_tag)
                session.flush()
                # Get all tags (existing + new)
                all_tags = set(existing_tags.values()).union(new_tags)
                setattr(obj, name, list(all_tags))
            elif isinstance(field, SelectField) and field.data is not None:
                value = dict(field.choices)[field.data]  # type:ignore
                if (value and obj.status is not None and obj.status.name !=
                        value):
                    setattr(obj, name, Status(name=value))
            else:
                field.populate_obj(obj, name)
