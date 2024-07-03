import os

from sqlalchemy import select
from privatim.forms.add_comment import CommentForm, NestedCommentForm
from privatim.forms.consultation_form import ConsultationForm
from privatim.models import Consultation
from privatim.models.consultation import Status, Tag
from privatim.i18n import _, translate
from pyramid.httpexceptions import HTTPFound

from privatim.models.file import SearchableFile
from privatim.utils import dictionary_to_binary, flatten_comments, maybe_escape

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.types import RenderDataOrRedirect, RenderData


def consultation_view(
    context: Consultation, request: 'IRequest'
) -> 'RenderData':

    request.add_action_menu_entry(
        translate(_('Edit Consultation')),
        request.route_url('edit_consultation', id=context.id),
    )
    top_level_comments = (c for c in context.comments if c.parent_id is None)
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
        'flattened_comments_tree': flatten_comments(top_level_comments)
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
    stmt = select(Consultation).order_by(Consultation.created)
    consultations = session.scalars(stmt).unique().all()

    return {
        'title': _('Consultations'),
        'activities': consultations,
        'show_add_button': True,
    }


def create_consultation_from_form(
    form: ConsultationForm, request: 'IRequest'
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

    consultation = Consultation(
        title=maybe_escape(form.title.data),
        description=maybe_escape(form.description.data),
        recommendation=maybe_escape(form.recommendation.data),
        status=status,
        secondary_tags=tags,
        creator=user
    )

    if form.files.data is None:
        return None

    for file in form.files.data:
        consultation.files.append(
            SearchableFile(
                file['filename'],
                dictionary_to_binary(file))
        )

    return consultation


def add_or_edit_consultation_view(
        context: Consultation | None, request: 'IRequest'
) -> 'RenderDataOrRedirect':

    if isinstance(context, Consultation):   # edit situation
        consultation = context
    else:  # add situation
        consultation = None

    form = ConsultationForm(context, request)
    target_url = request.route_url('activities')  # fallback
    session = request.dbsession

    if request.method == 'POST' and form.validate():
        if consultation is None:
            consultation = create_consultation_from_form(form, request)
            if consultation is not None:
                session.add(consultation)
                session.flush()
                target_url = request.route_url(
                    'consultation',
                    id=str(consultation.id)
                )

                message = _(
                    'Successfully added consultation "${name}"',
                    mapping={'name': form.title.data}
                )
                if not request.is_xhr:
                    request.messages.add(message, 'success')

        else:
            form.populate_obj(consultation)
            session.flush()
            target_url = request.route_url(
                'consultation',
                id=str(consultation.id)
            )
            message = _('Successfully edited consultation.')
            if not request.is_xhr:
                request.messages.add(message, 'success')

        if request.is_xhr:
            return {'redirect_to': target_url}
        else:
            return HTTPFound(location=target_url)
    elif not request.POST:
        form.process(obj=context)

    return {
        'form': form,
        'target_url': target_url,
        'title': (
            _('Add Consultation')
            if consultation is None
            else _('Edit Consultation')
        ),
    }
