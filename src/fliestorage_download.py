from typing import TYPE_CHECKING

from pyramid.response import Response

if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.models.attached_document import ConsultationDocument


def download_consultation_document(
        doc: 'ConsultationDocument',
        request: 'IRequest'
):

    response = Response(body=doc.content, request=request)
    response.headers['Content-Disposition'] = (
        f"inline; filename={doc.filename}"
    )
    response.headers['Content-Type'] = doc.content_type
    return response
