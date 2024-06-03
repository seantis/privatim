from privatim.forms.add_comment import CommentForm
from privatim.models import Consultation
from pyramid.httpexceptions import HTTPFound
from privatim.i18n import _
from privatim.i18n import translate

from typing import TYPE_CHECKING

from privatim.models.commentable import Comment

if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.types import MixedDataOrRedirect


def add_comment_view(
        context: Consultation,
        request: 'IRequest'
) -> 'MixedDataOrRedirect':

    assert isinstance(context, Consultation)
    # The target_url is a param because we want this to be generic.

    target_route_name = request.params.get('target_url')
    assert target_route_name, 'target_url is required.'
    target_url = request.route_url(target_route_name, id=context.id)

    form = CommentForm(context, request)
    session = request.dbsession
    if request.method == 'POST' and form.validate():
        comment = Comment(
            content=form.content.data,
            user=request.user,
            parent=None,
        )
        context.comments.append(comment)
        session.add(comment)
        message = _('Successfully added comment')
        request.messages.add(message, 'success')
        data = {
            'name': str(comment.content)
        }
        session.flush()
        data['message'] = translate(message, request.locale_name)

    return HTTPFound(location=target_url)
