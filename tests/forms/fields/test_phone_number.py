import pytest
from phonenumbers import PhoneNumberType
from wtforms import Form
from wtforms.validators import ValidationError

from privatim.forms.fields.phone_number import PhoneNumberField


class F(Form):
    phone_number = PhoneNumberField()
    mobile_number = PhoneNumberField(number_type=PhoneNumberType.MOBILE)


def test_process_formdata():
    form = F()
    field = form.phone_number

    field.process_formdata(['041 370 10 20'])
    assert field.data == '+41413701020'
    assert field.numobj is not None
    assert field.region == 'CH'


def test_process_formdata_missing():
    form = F()
    field = form.phone_number
    field.process_formdata([])
    assert field.data is None


def test_process_formdata_empty():
    form = F()
    field = form.phone_number

    field.process_formdata([''])
    assert field.data is None
    assert field.numobj is None
    assert field.region is None


def test_process_formdata_invalid():
    form = F()
    field = form.phone_number

    with pytest.raises(ValidationError, match=r'Invalid phone number'):
        field.process_formdata(['041 370 10 200'])
    assert field.data is None
    assert field.numobj is None
    assert field.region is None


def test_process_formdata_mobile():
    form = F()
    field = form.mobile_number

    field.process_formdata(['078 720 10 20'])
    assert field.data == '+41787201020'
    assert field.numobj is not None
    assert field.region == 'CH'


def test_process_formdata_invalid_mobile():
    form = F()
    field = form.mobile_number

    with pytest.raises(ValidationError, match=r'Invalid \${number_type}'):
        field.process_formdata(['041 370 10 20'])
    assert field.data is None
    assert field.numobj is None
    assert field.region is None


def test_value_formatting_existing():
    form = F()
    field = form.phone_number
    field.data = '+41413701020'
    assert field._value() == '+41 41 370 10 20'


def test_value_prioritize_raw_data():
    form = F()
    field = form.phone_number
    field.raw_data = ['0413701020']
    assert field._value() == '0413701020'


def test_value_dont_format_given():
    form = F()
    field = form.phone_number
    field.data = '041 370 10 20'
    field.raw_data = ['0413701020']
    assert field._value() == '0413701020'


def test_liechtenstein_mobile_nr():
    form = F()
    field = form.phone_number

    field.process_formdata(['+4233701020'])
    assert field.data == '+4233701020'
    assert field.numobj is not None
    assert field.region != 'LI'
