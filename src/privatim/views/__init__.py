from typing import TYPE_CHECKING

from pyramid.security import NO_PERMISSION_REQUIRED

from privatim.route_factories import (working_group_factory,
                                      _consultation_factory)
from privatim.views.activities import activities_overview
from privatim.views.consultation import consultation_view
from privatim.views.forbidden import forbidden_view
from privatim.views.home import home_view
from privatim.views.login import login_view
from privatim.views.logout import logout_view
from privatim.views.people import people_view
from privatim.views.working_groups import (groups_view,
                                           add_or_edit_group_view)

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

    # Neue Vernehmlassung Erfassen
    config.add_route(
        'add_consultation',
        '/consultations/add',
        factory=_consultation_factory
    )
    config.add_view(
        add_or_edit_group_view,
        route_name='add_consultation',
        renderer='templates/form.pt',
        xhr=False
    )
    config.add_view(
        add_or_edit_group_view,
        route_name='add_consultation',
        renderer='json',
        request_method='POST',
        xhr=True
    )

    # view for single consultation
    config.add_route(
        'consultation',
        '/consultations/{id}',
        factory=_consultation_factory
    )
    config.add_view(
        consultation_view,
        route_name='consultation',
        renderer='templates/consultation.pt',
    )

    config.add_route('people', '/people')
    config.add_view(
        people_view,
        route_name='people',
        renderer='templates/people.pt',
    )

    # working groups overview
    config.add_route('groups', '/groups')
    config.add_view(
        groups_view,
        route_name='groups',
        renderer='templates/working_groups.pt',)

    # single working group
    config.add_route(
        'add_working_group',
        '/groups/add',
        factory=working_group_factory
    )
    config.add_view(
        add_or_edit_group_view,
        route_name='add_working_group',
        renderer='templates/form.pt',
        xhr=False
    )
    config.add_view(
        add_or_edit_group_view,
        route_name='add_working_group',
        renderer='json',
        request_method='POST',
        xhr=True
    )
