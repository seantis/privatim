import os
import logging
from markupsafe import Markup
from sqlalchemy import select

from privatim.controls.controls import Button
from privatim.forms.add_comment import CommentForm, NestedCommentForm
from privatim.forms.consultation_form import ConsultationForm
from privatim.models import Consultation
from privatim.i18n import _
from pyramid.httpexceptions import HTTPFound

from privatim.models.file import SearchableFile
from privatim.utils import dictionary_to_binary, flatten_comments

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.types import RenderDataOrRedirect, RenderData

log = logging.getLogger(__name__)


def consultation_view(
    context: Consultation, request: 'IRequest'
) -> 'RenderData':

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
    return {
        'delete_title': _('Delete Consultation'),
        'title': Markup(context.title),
        '_id': context.id,
        'description': Markup(context.description),
        'recommendation': Markup(context.recommendation),
        'evaluation_result': Markup(context.evaluation_result),
        'decision': Markup(context.decision),
        'documents': [
            {
                'display_filename': trim_filename(doc.filename),
                'doc_content_type': doc.content_type,
                'download_url': request.route_url('download_file', id=doc.id),
            }
            for doc in context.files
        ],
        'status_name': _(context.status),
        'consultation_comment_form': CommentForm(context, request),
        'nested_comment_form': NestedCommentForm(context, request),
        'flattened_comments_tree': flatten_comments(top_level_comments,
                                                    request),
        'secondary_tags': context.secondary_tags
    }


def trim_filename(filename: str) -> str:
    name, extension = os.path.splitext(filename)
    max_name_length = 35 - len(extension)
    if len(filename) <= 35:
        return filename
    else:
        trimmed_name = name[:max_name_length-3] + ".."
        trimmed_filename = trimmed_name + extension
        return trimmed_filename


def consultations_view(request: 'IRequest') -> 'RenderData':
    session = request.dbsession
    stmt = (
        select(Consultation)
        .where(Consultation.is_latest_version == 1)
        .order_by(Consultation.created.desc())
    )

    consultations = [
        {
            '_id': _cons.id,
            'creator_pic_id': _cons.creator.picture.id if _cons.creator else
            None,
            'title': Markup(_cons.title),
            'creator': _cons.creator,
            'has_creator': _cons.creator is not None,
            'fullname': _cons.creator.fullname if _cons.creator else None,
            'description': Markup(_cons.description),
            'created': _cons.created
        } for _cons in session.scalars(stmt).unique().all()
    ]
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


def create_consultation_copy(
     request: 'IRequest', prev: Consultation
) -> Consultation:
    user = request.user

    new_consultation = Consultation(
        title=prev.title,
        description=prev.description,
        recommendation=prev.recommendation,
        evaluation_result=prev.evaluation_result,
        decision=prev.decision,
        status=prev.status,
        secondary_tags=prev.secondary_tags,
        creator=prev.creator,
        editor=user,
        files=list(prev.files),  # Create a new list to avoid modifying orig
        previous_version=prev,
        comments=list(prev.comments),  # New list
        is_latest_version=1
    )

    # Update the previous consultation
    prev.is_latest_version = 0
    prev.replaced_by = new_consultation

    return new_consultation


def edit_consultation_view(
    previous: Consultation, request: 'IRequest'
) -> 'RenderDataOrRedirect':
    session = request.dbsession
    target_url = request.route_url('consultation', id=previous.id)

    # Create a new consultation as a copy of the previous one
    breakpoint()  # len (files == 2) (expected)
    next = create_consultation_copy(
        request, previous
    )
    breakpoint()  # len(previous.files) == 0 (not expected)
    session.add(next)
    assert len(previous.files) == len(next.files)
    assert len(previous.comments) == len(next.comments)

    # Create the form with the new consultation
    form = ConsultationForm(next, request)
    if request.method == 'POST' and form.validate():
        # Populate the new consultation with form data
        form.populate_obj(next)
        session.add(next)
        session.flush()

        message = _('Successfully edited consultation.')
        if not request.is_xhr:
            request.messages.add(message, 'success')

        return HTTPFound(
            location=request.route_url(
                'consultation', id=str(next.id)
            )
        )
    elif not request.POST:
        form.process(obj=previous)

    session.expunge(next)
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
