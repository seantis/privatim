from wtforms import validators
from wtforms import TextAreaField, SubmitField
from privatim.forms.core import Form
from privatim.i18n import _, translate

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from typing import Any as Incomplete


class CommentForm(Form):
    def __init__(
            self,
            context: 'Incomplete',
            request: 'IRequest',
            title: str = _('Add Comment')
    ) -> None:

        self._title = title
        super().__init__(
            request.POST,
            obj=context,
            meta={'context': context, 'request': request},
        )

    content = TextAreaField(
        _('Comment'),
        validators=[validators.InputRequired()],
        render_kw={
            'rows': 4,
            'class': 'form-control shadow-none'
        },
    )
    submit = SubmitField(
        _('Add comment'), render_kw={'class': 'btn btn-primary btn-sm'}
    )
