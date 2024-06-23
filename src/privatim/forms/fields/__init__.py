from .fields import (
    ChosenSelectWidget,
    DateTimeLocalField,
    TimezoneDateTimeField,
    SearchableSelectField,
    UploadField,
    UploadMultipleField,
    # UploadOrSelectExistingMultipleFilesField,
)
from .transparent_form_field import TransparentFormField


from typing import Any, TYPE_CHECKING
if TYPE_CHECKING:
    from wtforms import Field


def FieldList(**fields: 'Field') -> 'TransparentFormField[Any]':
    from privatim.forms.core import Form

    form_class = type('TransparentForm', (Form,), fields)
    return TransparentFormField(form_class)


__all__ = (
    'FieldList',
    'TransparentFormField',
    "ChosenSelectWidget",
    "DateTimeLocalField",
    "TimezoneDateTimeField",
    "SearchableSelectField",
    "UploadField",
    "UploadMultipleField",
    # "UploadOrSelectExistingMultipleFilesField"
)
