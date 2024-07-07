import os

from sqlalchemy import select
from privatim.forms.add_comment import CommentForm, NestedCommentForm
from privatim.forms.consultation_form import ConsultationForm
from privatim.models import Consultation, GeneralFile
from privatim.models.consultation import Status, Tag
from privatim.i18n import _, translate
from pyramid.httpexceptions import HTTPFound

from privatim.models.profile_pic import get_or_create_default_profile_pic
from privatim.utils import dictionary_to_binary, flatten_comments, maybe_escape

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.types import RenderDataOrRedirect, RenderData


def consultation_view(
    context: Consultation, request: 'IRequest'
) -> 'RenderData':

    request.add_action_menu_entries(
        [
            (
                translate(_('Edit Consultation')),
                request.route_url('edit_consultation', id=context.id),
            ),
            (
                translate(_('Delete Consultation')),
                request.route_url('delete_consultation', id=context.id),
            ),
        ]
    )
    top_level_comments = (c for c in context.comments if c.parent_id is None)
    fallback_pic = request.route_url(
        'download_general_file', id=get_or_create_default_profile_pic(
            request.dbsession).id
    )
    return {
        'consultation': context,
        'documents': [
            {
                'display_filename': trim_filename(doc.filename),
                'doc_content_type': doc.content_type,
                'download_url': request.route_url(
                    'download_general_file', id=doc.id
                ),
            }
            for doc in context.files
        ],
        'consultation_comment_form': CommentForm(context, request),
        'nested_comment_form': NestedCommentForm(context, request),
        'flattened_comments_tree': flatten_comments(top_level_comments,
                                                    fallback_pic, request)
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
        .order_by(Consultation.created)
    )
    consultations = session.scalars(stmt).unique().all()

    return {
        'title': _('Consultations'),
        'activities': consultations,
        'show_add_button': True,
    }


def add_consultation_view(request: 'IRequest') -> 'RenderDataOrRedirect':
    form = ConsultationForm(None, request)

    target_url = request.route_url('activities')  # fallback
    if request.method == 'POST' and form.validate():
        session = request.dbsession
        user = request.user
        if form.status.data:
            status = Status(name=form.status.data)
            status.name = dict(form.status.choices)[form.status.data]
            session.add(status)
            session.flush()
        else:
            status = None

        if form.cantons.data:
            tags = [Tag(name=n) for n in form.cantons.raw_data]
            session.add_all(tags)
            session.flush()
        else:
            tags = None

        # Create a new Consultation instance
        new_consultation = Consultation(
            title=form.title.data,
            description=form.description.data,
            recommendation=form.recommendation.data,
            status=status,
            secondary_tags=tags,
            creator=user,
            editor=user,
            is_latest_version=1,
        )

        # Handle file uploads
        if form.files.data:
            for file in form.files.data:
                new_consultation.files.append(
                    GeneralFile(file['filename'], dictionary_to_binary(file))
                )

        session.add(new_consultation)
        session.flush()

        # target_url = request.route_url(
        #     'consultation',
        #     id=str(new_consultation.id),
        # )
        message = _(
            'Successfully added consultation "${name}"',
            mapping={'name': form.title.data}
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


def create_consultation_from_form(
        form: ConsultationForm, request: 'IRequest', prev: Consultation
) -> Consultation | None:

    session = request.dbsession
    status = Status(name=form.status.data)
    status.name = dict(form.status.choices)[form.status.data]

    session.add(status)
    session.flush()
    session.refresh(status)

    tags = [Tag(name=n) for n in form.cantons.raw_data]
    session.add_all(tags)
    session.flush()

    user = request.user
    if not user:
        return None

    files = []
    if form.files.data is not None:
        for file in form.files.data:
            if file.get('data', None) is not None:
                files.append(
                    GeneralFile(file['filename'], dictionary_to_binary(file))
                )
    else:
        files = prev.files

    assert prev.creator is not None
    new_consultation = Consultation(
        title=maybe_escape(form.title.data) or prev.title,
        description=maybe_escape(form.description.data) or prev.description,
        recommendation=maybe_escape(
            form.recommendation.data
        ) or prev.recommendation,
        status=status or prev.status,
        secondary_tags=tags or prev.secondary_tags,
        creator=prev.creator,
        editor=user,
        files=files,
        previous_version=prev,
        is_latest_version=1,
    )
    prev.replaced_by = new_consultation
    prev.is_latest_version = 0
    session.add(prev)
    return new_consultation


def edit_consultation_view(
    context: Consultation, request: 'IRequest'
) -> 'RenderDataOrRedirect':
    previous_consultation = context
    form = ConsultationForm(previous_consultation, request)

    target_url = request.route_url('activities')  # fallback
    if request.method == 'POST' and form.validate():
        session = request.dbsession
        new_consultation = create_consultation_from_form(
            form, request, previous_consultation
        )
        if new_consultation is None:
            raise ValueError('Could not create new consultation from form.')

        session.add(new_consultation)
        session.flush()

        message = _('Successfully edited consultation.')
        if not request.is_xhr:
            request.messages.add(message, 'success')
        return HTTPFound(
            location=request.route_url(
                'consultation', id=str(new_consultation.id)
            )
        )
    elif not request.POST:
        form.process(obj=context)

    return {
        'form': form,
        'title': _('Edit Consultation'),
        'target_url': target_url
    }


def delete_consultation_view(
    context: Consultation, request: 'IRequest'
) -> 'RenderDataOrRedirect':
    session = request.dbsession
    session.delete(context)
    target_url = request.route_url('activities')
    message = _('Successfully deleted consultation.')
    if not request.is_xhr:
        request.messages.add(message, 'success')
    return HTTPFound(location=target_url)
