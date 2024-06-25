from privatim.forms.add_comment import CommentForm
from privatim.models import Consultation
from pyramid.httpexceptions import HTTPFound, HTTPClientError, \
    HTTPInternalServerError
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
    form = CommentForm(context, request)
    session = request.dbsession

    # The target_url is a param because we want this to be generic.
    target_route_name = request.params.get('target_url')
    assert target_route_name, 'target_url is required.'
    target_url = request.route_url(target_route_name, id=context.id)

    parent_comment_id = request.params.get('parent_id')
    # assert parent_comment_id, 'parent_id is required.'

    if not (target_route_name and parent_comment_id):
        raise HTTPClientError()

    if parent_comment_id == 'root':
        parent = None
    else:
        parent = session.get(Comment, parent_comment_id)
        #  Unlikely to happen. Can only happen if another user has deleted
        #  his comment just in this moment
        if parent is None:
            raise HTTPInternalServerError()

    if request.method == 'POST' and form.validate():
        comment = Comment(
            content=form.content.data,
            user=request.user,
            parent=parent,
        )
        session.add(comment)
        context.comments.append(comment)
        message = _('Successfully added comment')
        request.messages.add(message, 'success')
        data = {
            'name': str(comment.content)
        }
        session.flush()
        data['message'] = translate(message, request.locale_name)

    return HTTPFound(location=target_url)
