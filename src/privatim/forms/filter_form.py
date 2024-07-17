from wtforms import SelectField, BooleanField, DateField

from privatim.forms.constants import cantons_named
from privatim.forms.core import Form
from wtforms.validators import Optional
from privatim.i18n import _


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from wtforms import Field


def render_filter_field(field: 'Field') -> str:
    if isinstance(field, BooleanField):
        return field(class_="form-check-input")
    else:
        return field(class_="form-control")


class FilterForm(Form):
    def __init__(
        self,
        request: 'IRequest',
    ) -> None:

        self._title = _('Filter')
        session = request.dbsession
        super().__init__(request.POST, meta={'dbsession': session})

    def get_type_fields(self) -> list[BooleanField]:
        return [self.consultation, self.meeting, self.comment]

    def get_date_fields(self) -> list[tuple[str, DateField]]:
        return [('datumVon', self.start_date), ('datumBis', self.end_date)]

    canton: SelectField = SelectField(
        _('Canton'),
        choices=[('all', _('all'))] + cantons_named,
        validators=[Optional()],
        render_kw={'class': 'form-select', 'id': 'kanton'},
    )

    consultation: BooleanField = BooleanField(
        _('Consultation'),
        default=True,
        render_kw={'class': 'form-check-input', 'id': 'vernehmlassung'},
    )
    meeting: BooleanField = BooleanField(
        _('Meeting'),
        default=True,
        render_kw={'class': 'form-check-input', 'id': 'sitzung'},
    )
    comment: BooleanField = BooleanField(
        _('Comment'),
        default=True,
        render_kw={'class': 'form-check-input', 'id': 'kommentar'},
    )

    start_date: DateField = DateField(
        _('Date from'),
        validators=[Optional()],
        render_kw={'class': 'form-control', 'id': 'datumVon'},
    )
    end_date: DateField = DateField(
        _('Date to'),
        validators=[Optional()],
        render_kw={'class': 'form-control', 'id': 'datumBis'},
    )
