from wtforms import validators
from wtforms import TextAreaField, SubmitField
from privatim.forms.core import Form
from privatim.i18n import _


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from typing import Any as Incomplete


class CommentForm(Form):
    def __init__(
            self,
            # Type is consultation, but could be Commentable if this will be
            # usd by other models in the future...
            context: 'Incomplete',
            request: 'IRequest',
    ) -> None:
        self._title = _('Add Comment')
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
        _('Add comment'), render_kw={'class': 'btn btn-primary btn-sm w-auto'}
    )


class NestedCommentForm(Form):
    def __init__(
            self,
            context: 'Incomplete',
            request: 'IRequest',
    ) -> None:
        self._title = _('Answer')
        super().__init__(
            request.POST,
            obj=context,
            meta={'context': context, 'request': request},
        )

    content = TextAreaField(
        _('Comment'),
        validators=[validators.InputRequired()],
        render_kw={
            'rows': 2,
            'class': 'form-control shadow-none'
        },
    )
    submit = SubmitField(
        _('Answer'), render_kw={'class': 'btn btn-primary btn-sm w-auto'}
    )
    cancel = SubmitField(
        _('Cancel'), render_kw={'class': 'btn btn-secondary btn-sm'}
    )
