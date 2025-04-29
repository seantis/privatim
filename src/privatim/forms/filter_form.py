from wtforms import DateField, SelectField
from privatim.forms.core import Form
from wtforms.validators import Optional

from privatim.forms.meeting_form import CheckboxField
from privatim.i18n import _


from typing import TYPE_CHECKING, Iterable
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.i18n import TranslationString


class FilterForm(Form):
    def __init__(
        self,
        request: 'IRequest',
        available_statuses: Iterable[tuple[str, 'TranslationString']]
    ) -> None:
        self._title = _('Filter')
        session = request.dbsession
        super().__init__(request.POST, meta={'dbsession': session})

        # Prepend the 'All Statuses' option
        status_choices = [('', _('All Statuses'))] + list(
            available_statuses
        )
        self.status.choices = status_choices

    consultation: CheckboxField = CheckboxField(
        _('Consultation'),
    )
    meeting: CheckboxField = CheckboxField(
        _('Meeting'),
    )

    start_date: DateField = DateField(
        _('Date from'),
        validators=[Optional()],
    )

    end_date: DateField = DateField(
        _('Date to'),
        validators=[Optional()],
    )

    status: SelectField = SelectField(
        _('Consultation Status'),
        validators=[Optional()],
        choices=[],
    )
