from typing import TYPE_CHECKING

from pyramid.httpexceptions import HTTPFound

if TYPE_CHECKING:
    from pyramid.interfaces import IRequest


def home_view(request: 'IRequest') -> HTTPFound:
    """ The home view is the view that is called after the user logs in."""
    if request.authenticated_userid:
        url = request.route_url('activities')  # default page redirect (
        # temporary)
    else:
        url = request.route_url('login')

    return HTTPFound(location=url)
