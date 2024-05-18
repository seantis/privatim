from sqlalchemy import select
from privatim.forms.consultation_form import ConsultationForm
from privatim.models import Consultation
from privatim.models.consultation import Status
from privatim.i18n import _
from pyramid.httpexceptions import HTTPFound
from privatim.models.attached_document import ConsultationDocument
from privatim.utils import dictionary_to_binary
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.types import RenderDataOrRedirect, RenderData
    from sqlalchemy.orm import Session


def consultation_view(
        context: Consultation, request: 'IRequest'
) -> 'RenderData':

    documents = []
    for doc in context.documents:
        documents.append({
            'document': doc,
            'download_url': request.route_url(
                'download_document',
                consultation_doc_id=doc.id
            )
        })

    return {
        'consultation': context,
        'documents': documents,
    }


def consultations_view(request: 'IRequest') -> 'RenderData':
    session = request.dbsession
    stmt = select(Consultation).order_by(Consultation.created)
    consultations = session.scalars(stmt).unique()
    return {'consultations': consultations}


def create_consultation_from_form(
    form: ConsultationForm, session: 'Session'
) -> Consultation | None:
    status = Status(name=form.status.name)
    session.add(status)
    session.flush()
    session.refresh(status)

    consultation = Consultation(
        title=form.title.data,
        description=form.description.data,
        comments=form.comments.data,
        recommendation=form.recommendation.data,
        status_id=status.id,
    )
    if form.documents.data is None:
        return None

    for file in form.documents.data:
        consultation.documents.append(
            ConsultationDocument(
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
    target_url = request.route_url('activities')  # change later
    session = request.dbsession

    if request.method == 'POST' and form.validate():
        if consultation is None:
            consultation = create_consultation_from_form(form, session)
            request.dbsession.add(consultation)
            message = _(
                'Successfully added consultation "${name}"',
                mapping={'name': form.title.data}
            )
            if not request.is_xhr:
                request.messages.add(message, 'success')

        # edit
        # form.populate_obj(group)
        if request.is_xhr:
            return {'redirect_to': target_url}
        else:
            return HTTPFound(location=target_url)

    if request.is_xhr:
        return {'errors': form.errors}
    else:
        return {
            'form': form,
            'redirect_after': target_url,
            'title': (
                _('Add Consultation')
                if consultation is None
                else _('Edit Consultation')
            ),
        }
