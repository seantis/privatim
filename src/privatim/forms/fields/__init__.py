from .fields import (
    TomSelectWidget,
    DateTimeLocalField,
    TimezoneDateTimeField,
    UploadField,
    UploadMultipleField,
    # UploadOrSelectExistingMultipleFilesField,
)
from .phone_number import PhoneNumberField
from .transparent_form_field import TransparentFormField


from typing import Any, TYPE_CHECKING
if TYPE_CHECKING:
    from wtforms import Field


def FieldList(**fields: 'Field') -> 'TransparentFormField[Any]':
    from privatim.forms.core import Form

    form_class = type('TransparentForm', (Form,), fields)
    return TransparentFormField(form_class)


__all__ = (
    'DateTimeLocalField',
    'FieldList',
    'PhoneNumberField',
    'TransparentFormField',
    'TimezoneDateTimeField',
    'TomSelectWidget',
    'UploadField',
    'UploadMultipleField',
    # 'UploadOrSelectExistingMultipleFilesField'
)
