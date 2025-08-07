from __future__ import annotations
from pyramid.httpexceptions import HTTPFound
from pyramid.security import forget


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest


def logout_view(request: 'IRequest') -> HTTPFound:
    headers = forget(request)
    url = request.route_url('login')
    return HTTPFound(location=url, headers=headers)
