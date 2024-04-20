from typing import TYPE_CHECKING

from pyramid.security import NO_PERMISSION_REQUIRED

from privatim.views.activities import activities_overview
from privatim.views.forbidden import forbidden_view
from privatim.views.home import home_view
from privatim.views.login import login_view
from privatim.views.logout import logout_view
from privatim.views.people import people_view
from privatim.views.working_groups import groups_view, group_view

if TYPE_CHECKING:
    from pyramid.config import Configurator


def includeme(config: 'Configurator') -> None:

    config.add_static_view(
        'static',
        'privatim:static',
        cache_max_age=3600
    )

    config.add_route('home', '/')
    config.add_view(home_view, route_name='home')

    config.add_forbidden_view(forbidden_view)

    # config.add_notfound_view(notfound_view)

    config.add_route('login', '/login')
    config.add_view(
        login_view,
        route_name='login',
        renderer='templates/login.pt',
        require_csrf=False,
        permission=NO_PERMISSION_REQUIRED,
    )

    config.add_route('logout', '/logout')
    config.add_view(logout_view, route_name='logout')

    config.add_route('activities', '/activities')
    config.add_view(
        activities_overview,
        route_name='activities',
        renderer='templates/consultations.pt',
    )

    config.add_route('people', '/people')
    config.add_view(
        people_view,
        route_name='people',
        renderer='templates/people.pt',
    )

    config.add_route('groups', '/groups')
    config.add_view(
        groups_view,
        route_name='groups',
        renderer='templates/groups.pt',
    )

    config.add_route('group', '/group')
    config.add_view(
        group_view,
        route_name='group',
        renderer='templates/form.pt',
    )
