from __future__ import annotations
from typing import TYPE_CHECKING

from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPFound

if TYPE_CHECKING:
    from pyramid.interfaces import IRequest


def forbidden_view(request: 'IRequest') -> HTTPForbidden | HTTPFound:
    if request.user:
        return HTTPForbidden()

    url = request.route_url('login')
    return HTTPFound(location=url)
