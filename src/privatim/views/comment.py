from privatim.forms.add_comment import CommentForm
from privatim.models import Consultation
from pyramid.httpexceptions import HTTPFound, HTTPClientError, HTTPNotFound
from privatim.i18n import _
from privatim.i18n import translate
from privatim.models.commentable import Comment
from privatim.utils import maybe_escape


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.types import MixedDataOrRedirect


def delete_comment_view(
    context: Comment, request: 'IRequest'
) -> 'MixedDataOrRedirect':
    session = request.dbsession
    consultation_id = context.get_commentable().id
    session.delete(context)
    message = _('Successfully deleted comment')
    request.messages.add(message, 'success')
    session.flush()

    return HTTPFound(
        location=request.route_url('consultation', id=consultation_id)
    )


def edit_comment_view(
        context: Comment, request: 'IRequest'
) -> 'MixedDataOrRedirect':
    form = CommentForm(context, request)
    session = request.dbsession

    if request.method == 'POST' and form.validate():
        context.content = maybe_escape(form.content.data)
        message = _('Successfully edited comment')
        request.messages.add(message, 'success')
        data = {
            'name': str(context.content)
        }
        session.flush()
        data['message'] = translate(message, request.locale_name)
        if request.is_xhr:
            return {
                'success': True,
                'message': translate(message, request.locale_name),
                'content': context.content
            }

    return HTTPFound(
        location=request.route_url('comment', id=context.id)
    )


def add_comment_view(
        context: Consultation, request: 'IRequest'
) -> 'MixedDataOrRedirect':

    form = CommentForm(context, request)
    session = request.dbsession

    # The target_url is a param because we want this to be generic. (We take
    # the possibility into account that other models are commentable in the
    # future, in that case, we'd like to re-use this view. Thus we don't hard-
    # code `target` to consultation.)
    target_route_name = request.params.get('target_url')
    assert target_route_name, 'target_url is required.'
    target_url = request.route_url(target_route_name, id=context.id)

    parent_comment_id = request.params.get('parent_id')
    if not (target_route_name and parent_comment_id):
        raise HTTPClientError()

    if parent_comment_id == 'root':
        parent = None
    else:
        parent = session.get(Comment, parent_comment_id)
        if parent is None:
            #  Unlikely to happen. Can only happen if another user has deleted
            #  his comment just in this moment
            raise HTTPNotFound('Parent comment not found')

    if request.method == 'POST' and form.validate():
        assert form.content.data is not None
        comment = Comment(
            content=maybe_escape(form.content.data),
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
