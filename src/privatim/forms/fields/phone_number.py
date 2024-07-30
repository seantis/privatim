import babel
from phonenumbers import format_number
from phonenumbers import is_valid_number
from phonenumbers import number_type as number_type_for_number
from phonenumbers import NumberParseException
from phonenumbers import parse as parse_phonenumber
from phonenumbers import PhoneNumberFormat
from phonenumbers import PhoneNumberType
from phonenumbers import region_code_for_number
from phonenumbers import SUPPORTED_REGIONS
from phonenumbers import supported_types_for_region
from wtforms import StringField
from wtforms.validators import ValidationError

from privatim.i18n import translate
from privatim.i18n import _


from typing import Any
from typing import ClassVar
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from phonenumbers import PhoneNumber
    from typing_extensions import Self
    from wtforms.fields.core import _Widget

    from privatim.forms.types import _FormT
    from privatim.forms.types import Validators


_locale = babel.Locale('en')


class PhoneNumberField(StringField):

    supported_regions: ClassVar[tuple[str, ...]] = tuple(
        # NOTE: This is fine to ignore since SUPPORTED_REGIONS
        #       should only contain strings
        region  # type:ignore
        for region in _locale.territories
        if region in SUPPORTED_REGIONS
    )
    data: str | None
    number_type: int | None

    def __init__(
        self,
        label: str | None = None,
        validators: 'Validators[_FormT, Self] | None' = None,
        # FIXME: PhoneNumberType is not an enum
        number_type: int | None = None,
        *,
        widget: '_Widget[Self] | None' = None,
        **kwargs: Any
    ):
        super().__init__(label, validators, widget=widget, **kwargs)
        self.number_type = number_type

    def format_number_type(self) -> str:
        if self.number_type == PhoneNumberType.FIXED_LINE:
            return translate(_('fixed line number'))
        elif self.number_type == PhoneNumberType.MOBILE:
            return translate(_('mobile number'))
        else:
            # NOTE: For now we only map the two types we need.
            return 'unknown type'

    def process_formdata(self, valuelist: list[Any]) -> None:
        if valuelist:
            number = valuelist[0]
            number = number.strip()

            if not number:
                self.raw_data = None
                self.data = None
                self._numobj = None
                self._region = None
                return

            try:
                # TODO: We hardcode the region CH for now, we may want
                #       to provide a more flexible widget, like the one
                #       used in OCQMS in the future. International numbers
                #       can still be entered using the country code, so
                #       this region provides a shortcut for CH numbers
                numobj = parse_phonenumber(number, region='CH')
                number = format_number(numobj, PhoneNumberFormat.E164)
                region = region_code_for_number(numobj)
            except NumberParseException:
                # NOTE: We could give a more specific error message
                raise ValidationError(_('Invalid phone number')) from None

            if region not in self.supported_regions:
                raise ValidationError(_('Invalid phone number region'))

            if not is_valid_number(numobj):
                raise ValidationError(
                    _('Invalid phone number for selected region')
                )

            if self.number_type in supported_types_for_region(region):
                # Validate type if we can
                number_type = number_type_for_number(numobj)
                if number_type == PhoneNumberType.FIXED_LINE_OR_MOBILE:
                    if self.number_type in (
                        PhoneNumberType.FIXED_LINE,
                        PhoneNumberType.MOBILE
                    ):
                        # make aggregate types match.
                        number_type = self.number_type
                if number_type != self.number_type:
                    raise ValidationError(_(
                        'Invalid ${number_type}',
                        mapping={'number_type': self.format_number_type()}
                    ))

            self.data = number
            self._numobj = numobj
            self._region = region
        else:
            self.data = None
            self._numobj = None
            self._region = None

    def _value(self) -> str:
        if self.raw_data:
            value = self.raw_data[0]
            return value if isinstance(value, str) else ''
        elif not self.data:
            return ''
        elif self.numobj:
            return format_number(self.numobj, PhoneNumberFormat.INTERNATIONAL)
        elif self.data:
            return self.data
        return ''

    @property
    def numobj(self) -> 'PhoneNumber | None':
        if not hasattr(self, '_numobj'):
            if not self.data:
                return None

            try:
                self._numobj = parse_phonenumber(self.data)
            except NumberParseException:
                self._numobj = None
        return self._numobj

    @property
    def region(self) -> str | None:
        if not hasattr(self, '_region'):
            if self.numobj is not None:
                self._region = region_code_for_number(self.numobj)
            else:
                self._region = None
        return self._region
