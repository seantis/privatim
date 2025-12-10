from __future__ import annotations
from typing import TYPE_CHECKING

from pyramid.httpexceptions import HTTPFound

if TYPE_CHECKING:
    from pyramid.interfaces import IRequest


def home_view(request: IRequest) -> HTTPFound:
    """ The home view is the view that is called after the user logs in."""
    return HTTPFound(
        location=(
            request.route_url('activities')
            if request.authenticated_userid
            else request.route_url('login')
        )
    )


class SentryWorks(Exception):
    pass


def sentry_test_view(request: IRequest) -> HTTPFound:
    # test sentry working:
    raise SentryWorks('Test Sentry')
