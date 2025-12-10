from __future__ import annotations
from pyramid.httpexceptions import HTTPFound
from privatim.models.file import GeneralFile
from pyramid.response import Response
from privatim.i18n import _
from privatim.i18n import translate


from typing import TYPE_CHECKING

from privatim.orm.abstract import AbstractFile

if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.types import XHRDataOrRedirect


def download_general_file_view(
    file: AbstractFile, request: IRequest
) -> Response:
    """ Downloads any file. Anyone who knows the link can download the file."""

    assert isinstance(file, AbstractFile)
    response = Response(body=file.content, request=request)
    response.headers['Content-Disposition'] = (
        f"inline; filename={file.filename}"
    )
    response.headers['Content-Type'] = file.file.content_type
    return response


def delete_general_file_view(
    context: GeneralFile, request: IRequest
) -> XHRDataOrRedirect:

    """ Deletes a file. """
    assert isinstance(context, GeneralFile)

    # The target_url is a param because we want this to be generic.
    target_route_name = request.params.get('target_url')
    assert target_route_name, 'target_url is required.'
    target_url = request.route_url(target_route_name)
    title = context.filename
    session = request.dbsession
    session.delete(context)

    message = _(
        'Successfully deleted file "${title}"',
        mapping={'name': title}
    )

    if request.is_xhr:
        data = {
            'name': context.filename,
            'redirect_url': target_url
        }
        request.dbsession.flush()
        data['message'] = translate(message, request.locale_name)
        return data
    else:
        return HTTPFound(location=target_url)
