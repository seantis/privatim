from markupsafe import Markup
from sqlalchemy import select
from privatim.controls.controls import Button
from privatim.forms.add_comment import CommentForm, NestedCommentForm
from privatim.forms.consultation_form import ConsultationForm
from privatim.models import Consultation
from privatim.i18n import _
from privatim.i18n import translate
from pyramid.httpexceptions import HTTPFound
import logging
from privatim.models.file import SearchableFile
from privatim.utils import (
    dictionary_to_binary,
    flatten_comments,
    get_previous_versions,
)


from typing import TYPE_CHECKING

from privatim.views.utils import trim_filename

if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.types import RenderDataOrRedirect, RenderData


logger = logging.getLogger(__name__)


def consultation_view(
    context: Consultation, request: 'IRequest'
) -> 'RenderData':
    session = request.dbsession
    request.add_action_menu_entries([
        Button(
            title=_('Edit'),
            url=request.route_url('edit_consultation', id=context.id),
            icon='edit',
            description=_('Edit Consultation'),
            css_class='dropdown-item',
        ),
        Button(
            url=request.route_url('delete_consultation', id=context.id),
            icon='trash',
            title=_('Delete'),
            description=_('Delete Consultation'),
            css_class='dropdown-item',
            modal='#delete-xhr',
            data_item_title=context.title,
        ),
    ])
    top_level_comments = (c for c in context.comments if c.parent_id is None)
    previous_versions = [context] + get_previous_versions(session, context)

    is_old_version = not context.is_latest()
    latest_version = context.get_latest_version(session)

    return {
        'delete_title': _('Delete Consultation'),
        'title': context.title,
        '_id': context.id,
        'description': Markup(context.description),
        'recommendation': Markup(context.recommendation),
        'evaluation_result': Markup(context.evaluation_result),
        'decision': Markup(context.decision),
        'is_old_version': is_old_version,
        'latest_version_url': (
            request.route_url('consultation', id=latest_version.id)
            if latest_version else None
        ),
        'previous_versions': [
            {
                'created': version.created,
                'editor_name': version.editor.fullname
                if version.editor
                else None
            }
            for version in previous_versions
        ],
        'documents': [
            {
                'display_filename': trim_filename(doc.filename),
                'doc_content_type': doc.content_type,
                'download_url': request.route_url('download_file', id=doc.id),
            }
            for doc in context.files
        ],
        'status_name': translate(_(context.status)),
        'consultation_comment_form': CommentForm(context, request),
        'nested_comment_form': NestedCommentForm(context, request),
        'flattened_comments_tree': flatten_comments(
            top_level_comments, request
        ),
        'secondary_tags': context.secondary_tags,
        'navigate_back_up': request.route_url('consultations'),
    }


def consultations_view(request: 'IRequest') -> 'RenderData':
    session = request.dbsession
    stmt = (
        select(Consultation)
        .where(Consultation.is_latest_version == 1)
        .order_by(Consultation.created.desc())
    )

    consultations = tuple(
        {
            '_id': _cons.id,
            'editor_pic_id': _cons.editor.picture.id if _cons.editor else
            None,
            'title': _cons.title,
            'editor_name': _cons.editor.fullname if _cons.editor
            else _('Deleted User'),
            'description': Markup(_cons.description),
            'updated': _cons.updated,
        } for _cons in session.scalars(stmt).unique().all()
    )
    return {
        'title': _('Consultations'),
        'consultations': consultations,
    }


def add_consultation_view(request: 'IRequest') -> 'RenderDataOrRedirect':
    form = ConsultationForm(None, request)

    target_url = request.route_url('activities')  # fallback
    if request.method == 'POST' and form.validate():
        session = request.dbsession
        user = request.user
        # Create a new Consultation instance
        assert form.title.data is not None
        secondary_tags = form.secondary_tags.data or []
        new_consultation = Consultation(
            title=form.title.data,
            description=form.description.data,
            recommendation=form.recommendation.data,
            evaluation_result=form.evaluation_result.data,
            decision=form.decision.data,
            status=form.status.data,
            secondary_tags=secondary_tags,
            creator=user,
            editor=user,
            is_latest_version=1,
        )

        # Handle file uploads
        if form.files.data:
            for file in form.files.data:
                if file:
                    new_consultation.files.append(
                        SearchableFile(
                            file['filename'],
                            dictionary_to_binary(file),
                            content_type=file['mimetype']
                        )
                    )
        session.add(new_consultation)
        session.flush()

        message = _(
            'Successfully added consultation'
        )
        if not request.is_xhr:
            request.messages.add(message, 'success')
        return HTTPFound(
            location=request.route_url(
                'consultation', id=str(new_consultation.id)
            )
        )

    return {
        'form': form,
        'title': _('Add Consultation'),
        'target_url': target_url
    }


def edit_consultation_view(
    previous: Consultation, request: 'IRequest'
) -> 'RenderDataOrRedirect':
    session = request.dbsession
    target_url = request.route_url('consultation', id=previous.id)
    # Create a new consultation (copy)
    next_cons = Consultation(
        title=previous.title,
        description=previous.description,
        recommendation=previous.recommendation,
        evaluation_result=previous.evaluation_result,
        decision=previous.decision,
        status=previous.status,
        secondary_tags=previous.secondary_tags,
        creator=previous.creator,
        editor=request.user,
        files=list(previous.files),
        previous_version=previous,
        comments=list(previous.comments),  # New list
        is_latest_version=1,
    )
    session.add(next_cons)
    assert len(previous.comments) == len(next_cons.comments)

    # Create the form with the new consultation
    form = ConsultationForm(next_cons, request)
    if request.method == 'POST' and form.validate():

        # Populate the new consultation with form data
        form.populate_obj(next_cons)
        session.add(next_cons)

        # Update the previous consultation
        previous.is_latest_version = 0
        previous.replaced_by = next_cons
        session.add(previous)
        session.flush()
        message = _('Successfully edited consultation.')
        if not request.is_xhr:
            request.messages.add(message, 'success')

        return HTTPFound(
            location=request.route_url(
                'consultation', id=str(next_cons.id)
            )
        )

    session.expunge(next_cons)
    return {
        'form': form,
        'title': _('Edit Consultation'),
        'target_url': target_url,
    }


def delete_consultation_view(
        context: Consultation, request: 'IRequest'
) -> 'RenderDataOrRedirect':
    session = request.dbsession
    target_url = request.route_url('activities')

    # SoftDeleteMixin should take care of the files
    session.delete(context, soft=True)
    session.flush()

    message = _('Consultation moved to the paper basket')
    request.messages.add(message, 'success')
    if request.is_xhr:
        return {
            'success': message,
            'redirect_url': request.route_url('activities'),
        }

    return HTTPFound(location=target_url)
