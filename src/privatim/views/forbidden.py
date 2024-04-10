from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPFound
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from pyramid.interfaces import IRequest



def forbidden_view(request: 'IRequest') -> HTTPForbidden | HTTPFound:
    if request.user:
        return HTTPForbidden()

    url = request.route_url('login')
    return HTTPFound(location=url)
