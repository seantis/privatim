from __future__ import annotations
from wtforms.fields.simple import SearchField
from wtforms.validators import DataRequired
from privatim.forms.core import Form
from privatim.i18n import _


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest


class SearchForm(Form):

    def __init__(
            self,
            request: 'IRequest',
    ) -> None:
        session = request.dbsession
        super().__init__(
            request.POST if request.POST else None,
            meta={
                'dbsession': session
            }
        )
    term = SearchField(
        _('Search'),
        [DataRequired()],
        render_kw={
        },
    )
