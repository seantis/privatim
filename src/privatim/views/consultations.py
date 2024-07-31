import os
import logging
from markupsafe import Markup
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

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
    from privatim.orm import FilteredSession
    from pyramid.interfaces import IRequest
    from privatim.types import RenderDataOrRedirect, RenderData

log = logging.getLogger(__name__)


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
    return {
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
        'status_name': context.status.name if context.status else '',
        'consultation_comment_form': CommentForm(context, request),
        'nested_comment_form': NestedCommentForm(context, request),
        'flattened_comments_tree': flatten_comments(top_level_comments,
                                                    request),
        'secondary_tags': tuple(t.name for t in context.secondary_tags)
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
        'show_add_button': True,
        'show_filter': False,
    }


def add_consultation_view(request: 'IRequest') -> 'RenderDataOrRedirect':
    form = ConsultationForm(None, request)

    target_url = request.route_url('activities')  # fallback
    if request.method == 'POST' and form.validate():
        session = request.dbsession
        user = request.user
        if form.status.data:
            status = Status(name=form.status.data)
            status.name = dict(form.status.choices)[  # type:ignore
                form.status.data
            ]
            session.add(status)
            session.flush()
        else:
            status = None

        if form.secondary_tags.data:
            tags = [Tag(name=n) for n in form.secondary_tags.raw_data or ()]
            session.add_all(tags)
            session.flush()
        else:
            tags = None

        # Create a new Consultation instance
        assert form.title.data is not None
        new_consultation = Consultation(
            title=form.title.data,
            description=form.description.data,
            recommendation=form.recommendation.data,
            evaluation_result=form.evaluation_result.data,
            decision=form.decision.data,
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
                    SearchableFile(
                        file['filename'],
                        dictionary_to_binary(file)
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


def create_consultation_from_form(
        form: ConsultationForm, request: 'IRequest', prev: Consultation
) -> Consultation | None:

    session = request.dbsession
    status = Status(name=form.status.data)
    status.name = dict(form.status.choices)[form.status.data]  # type:ignore

    session.add(status)
    session.flush()
    session.refresh(status)

    tags = [Tag(name=n) for n in form.secondary_tags.raw_data or ()]
    session.add_all(tags)
    session.flush()

    user = request.user
    if not user:
        return None

    # We create a new list new_files to hold the SearchableFile instances for
    # the new consultation.
    # this preserves history
    previous_files = []
    for file in prev.files:
        new_file = SearchableFile(
            filename=file.filename,
            content=file.content
        )
        previous_files.append(new_file)

    new_files = []
    if form.files.data is not None:
        for new_file_from_form in form.files.data:
            if new_file_from_form.get('data', None) is not None:
                new_files.append(SearchableFile(
                    filename=new_file_from_form['filename'],
                    content=dictionary_to_binary(new_file_from_form)
                ))

    seen = set()
    combined = [*previous_files, *new_files]
    for f in combined:
        if f.filename not in seen:
            seen.add(f.filename)

    combined = [file for file in combined if file.filename in seen]

    assert prev.creator is not None
    new_consultation = Consultation(
        title=maybe_escape(form.title.data) or prev.title,
        description=maybe_escape(form.description.data) or prev.description,
        recommendation=maybe_escape(
            form.recommendation.data) or prev.recommendation,
        evaluation_result=maybe_escape(
            form.evaluation_result.data) or prev.evaluation_result,
        decision=maybe_escape(form.decision.data) or prev.decision,
        status=status or prev.status,
        secondary_tags=tags or prev.secondary_tags,
        creator=prev.creator,
        editor=user,
        files=combined,
        previous_version=prev,
        # If new files are present reindexing should insert the searchable text
        searchable_text_de_CH=prev.searchable_text_de_CH if not new_files
        else None,
        comments=prev.comments,
        is_latest_version=1
    )
    prev.is_latest_version = 0
    prev.replaced_by = new_consultation
    session.add(prev)
    new_consultation.reindex_files()
    return new_consultation


def edit_consultation_view(
    previous_consultation: Consultation, request: 'IRequest'
) -> 'RenderDataOrRedirect':

    form = ConsultationForm(previous_consultation, request)

    target_url = request.route_url('activities')  # fallback
    if request.method == 'POST' and form.validate():
        form.populate_obj(previous_consultation)
        session = request.dbsession
        new_consultation = create_consultation_from_form(
            form, request, previous_consultation
        )
        if new_consultation is None:
            raise ValueError('Could not create new consultation from form.')

        session.add(new_consultation)
        session.flush()
        session.refresh(new_consultation)

        message = _('Successfully edited consultation.')
        if not request.is_xhr:
            request.messages.add(message, 'success')
        return HTTPFound(
            location=request.route_url(
                'consultation', id=str(new_consultation.id)
            )
        )
    elif not request.POST:
        form.process(obj=previous_consultation)

    return {
        'form': form,
        'title': _('Edit Consultation'),
        'target_url': target_url
    }


def delete_consultation_chain(
    session: 'FilteredSession', consultation: Consultation
) -> list[str]:
    """
    Go backwards through the version history of the consultations linked
    list and delete all of them. We need to make sure we delete associated
    Status and SearchableAssociatedFile from association table.
    """
    ids_to_delete = []
    current = consultation
    while current:
        ids_to_delete.append(str(current.id))
        current = current.previous_version  # type:ignore

    # Fetch all consultations with their associated data
    consultations = (
        session.execute(
            select(Consultation)
            .options(
                joinedload(Consultation.status),
                joinedload(Consultation.files),
                joinedload(Consultation.secondary_tags),
                joinedload(Consultation.comments),
            )
            .where(Consultation.id.in_(ids_to_delete))
        )
        .unique()
        .scalars()
        .all()
    )

    for consultation in consultations:
        try:
            # Handle associated files
            for file in consultation.files:
                try:
                    session.delete(file)
                except IntegrityError:
                    log.warning(
                        f"Associated file {file.id} for consultation "
                        f"{consultation.id} not found or already deleted."
                    )
                    session.rollback()

            # Handle secondary tags
            for tag in consultation.secondary_tags:
                try:
                    consultation.secondary_tags.remove(tag)
                except ValueError:
                    log.warning(
                        f"Secondary tag {tag.id} for consultation "
                        f"{consultation.id} not found or already removed."
                    )

            # Handle comments
            for comment in consultation.comments:
                try:
                    session.delete(comment)
                except IntegrityError:
                    log.warning(
                        f"Comment {comment.id} for consultation "
                        f"{consultation.id} not found or already deleted."
                    )
                    session.rollback()

            # Handle status
            if consultation.status:
                try:
                    session.delete(consultation.status)
                except IntegrityError:
                    log.warning(
                        f"Status for consultation {consultation.id} not found "
                        f"or already deleted."
                    )
                    session.rollback()

            # Delete the consultation
            session.delete(consultation)
            session.flush()

        except Exception as e:
            log.error(f'Error deleting consultation {consultation.id}: {e}')
            session.rollback()
            raise

    return ids_to_delete


def delete_consultation_view(
    context: Consultation, request: 'IRequest'
) -> 'RenderDataOrRedirect':
    session = request.dbsession

    start_id = context.id
    start = session.get(Consultation, start_id)
    if start is not None:
        assert isinstance(start, Consultation)
        session.delete(context)
        session.flush()
        # delete_consultation_chain(session, start)  # type: ignore[arg-type]
        message = _('Successfully deleted consultation.')
        if not request.is_xhr:
            request.messages.add(message, 'success')

    target_url = request.route_url('activities')
    return HTTPFound(location=target_url)
