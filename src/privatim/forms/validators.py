from cgi import FieldStorage
from wtforms.validators import DataRequired
from wtforms.validators import Optional
from wtforms.validators import StopValidation
from wtforms.validators import ValidationError
import re
from privatim.i18n import _


from typing import Any
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from abc import abstractmethod
    from wtforms import Field, Form
    from collections.abc import Sequence


email_regex = re.compile(
    r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
)
password_regex = re.compile(
    r'^(?=.{8,})(?=.*[a-z])(?=.*[A-Z])(?=.*[\d])(?=.*[\W]).*$'
)


class OptionalIf(Optional):
    """
    Marks a field optional if another field is set.
    """

    def __init__(self, check_field: str, *args: str, **kwargs: str):
        self.check_field = check_field
        super(OptionalIf, self).__init__(*args, **kwargs)

    def __call__(self, form: 'Form', field: 'Field') -> None:
        other_field = form._fields.get(self.check_field)

        if other_field is None:
            raise Exception('no field named "%s" in form' %
                            self.other_field_name)

        if bool(other_field.data):
            super(OptionalIf, self).__call__(form, field)


class FileRequired(DataRequired):
    """
    Validates that data is a FieldStorage object.

    Implementation heavily insipired by Flask-WTFs FileRequired:
    https://flask-wtf.readthedocs.io/en/0.15.x/api/#flask_wtf.file.FileRequired
    """

    def __call__(self, form: 'Form', field: 'Field') -> None:
        if not (isinstance(field.data, FieldStorage)):
            raise StopValidation(
                self.message or field.gettext("This field is required.")
            )


class FileExtensionsAllowed:
    """
    Validates that the data has an allowed file extension.

    NOTE: Validates only the file extension - there is no guarantee that the
    file is actually of the format the extension claims to be.

    Implementation heavily insipired by Flask-WTFs FileAllowed:
    https://flask-wtf.readthedocs.io/en/0.15.x/api/#flask_wtf.file.FileAllowed
    """

    def __init__(
        self,
        extensions: 'Sequence[str]',
        message: str | None = None
    ) -> None:
        self.extensions = extensions
        self.message = message

    def __call__(self, form: 'Form', field: 'Field') -> None:
        filename = field.data.filename.lower()

        if any(filename.endswith(ext) for ext in self.extensions):
            return

        raise StopValidation(
            self.message or
            field.gettext(
                "File does not have an approved extension: {extensions}"
            ).format(extensions=", ".join(self.extensions))
        )


def email_validator(form: 'Form', field: 'Field') -> None:
    if not email_regex.match(field.data):
        raise ValidationError('Not a valid email.')


def password_validator(form: 'Form', field: 'Field') -> None:
    password = form.password.data
    password_confirmation = form.password_confirmation.data

    if not password or not password_confirmation:
        return

    if password != password_confirmation:
        raise ValidationError('Password and confirmation do not match.')

    if not password_regex.match(password):
        msg = (
            'Password must have minimal length of 8 characters, contain '
            'one upper case letter, one lower case letter, one digit and '
            'one special character.'
        )
        raise ValidationError(msg)


class Immutable:
    """
    This marker class is only useful as a common base class to the derived
    validators.

    Our custom form class  will skip any fields that have a validator derived
     from this class when executing Form.populate_obj()
    """
    field_flags: dict[str, Any] = {}
    if TYPE_CHECKING:
        @abstractmethod
        def __call__(self, form: 'Form', field: 'Field') -> None: ...


class Disabled(Immutable):
    """
    Sets a field to disabled.

    Validation fails if formdata is supplied anyways.
    """

    def __init__(self) -> None:
        self.field_flags = {'disabled': True, 'aria_disabled': 'true'}

    def __call__(self, form: 'Form', field: 'Field') -> None:
        if field.raw_data is not None:
            raise ValidationError(_('This field is disabled.'))


class ReadOnly(Immutable):
    """
    Sets a field to disabled.

    Validation fails if formdata is supplied anyways.
    """

    def __init__(self) -> None:
        self.field_flags = {'readonly': True, 'aria_readonly': 'true'}

    def __call__(self, form: 'Form', field: 'Field') -> None:
        if field.data != field.object_data:
            raise ValidationError(_('This field is read only.'))
