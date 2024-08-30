from privatim.forms.core import Form
from privatim.forms.fields.fields import ConstantTextAreaField
from privatim.i18n import _
from wtforms import SubmitField
from wtforms import validators


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from typing import Any as Incomplete


class CommentForm(Form):

    def __init__(
        self,
        context: 'Incomplete',
        request: 'IRequest',
    ) -> None:
        self._title = _('Add Comment')
        super().__init__(
            request.POST if request.POST else None,
            obj=context,
            meta={'context': context, 'request': request},
        )

    content = ConstantTextAreaField(
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
            request.POST if request.POST else None,
            obj=context,
            meta={'context': context, 'request': request},
        )

    content = ConstantTextAreaField(
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
