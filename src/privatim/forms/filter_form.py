from __future__ import annotations
from wtforms import DateField
from privatim.forms.core import Form
from wtforms.validators import Optional

from privatim.forms.meeting_form import CheckboxField
from privatim.i18n import _


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest


class FilterForm(Form):
    def __init__(
        self,
        request: IRequest,
    ) -> None:
        self._title = _('Filter')
        session = request.dbsession
        super().__init__(request.POST, meta={'dbsession': session})

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
