from typing import TYPE_CHECKING

from pyramid.security import NO_PERMISSION_REQUIRED

from fliestorage_download import download_consultation_document
from privatim.route_factories import (working_group_factory,
                                      consultation_factory, person_factory,
                                      meeting_factory,
                                      consultation_document_factory)
from privatim.views.activities import activities_overview
from privatim.views.consultations import (add_or_edit_consultation_view,
                                          consultation_view,
                                          consultations_view)
from privatim.views.forbidden import forbidden_view
from privatim.views.home import home_view
from privatim.views.login import login_view
from privatim.views.logout import logout_view
from privatim.views.people import people_view, person_view
from privatim.views.working_groups import (working_groups_view,
                                           add_or_edit_group_view,
                                           working_group_view)

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
        renderer='templates/activities.pt',
    )

    # Adding a new consultation
    config.add_route(
        'add_consultation',
        '/consultations/add',
        factory=consultation_factory
    )
    config.add_view(
        add_or_edit_consultation_view,
        route_name='add_consultation',
        renderer='templates/form.pt',
        xhr=False
    )
    config.add_view(
        add_or_edit_consultation_view,
        route_name='add_consultation',
        renderer='json',
        request_method='POST',
        xhr=True
    )

    # view for single consultation
    config.add_route(
        'consultation',
        '/consultations/{id}',
        factory=consultation_factory
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

    # consultations overview
    config.add_route('consultations', '/consultations')
    config.add_view(
        consultations_view,
        route_name='consultations',
        renderer='templates/consultations.pt'
    )

    # working groups overview
    config.add_route('working_groups', '/working_groups')
    config.add_view(
        working_groups_view,
        route_name='working_groups',
        renderer='templates/working_groups.pt',)

    # view for single working_group
    config.add_route(
        'working_group',
        '/working_groups/{id}',
        factory=working_group_factory
    )
    config.add_view(
        working_group_view,
        route_name='working_group',
        renderer='templates/working_group.pt',
    )

    # adding a single working group
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

    # Add meeting per working_group
    config.add_route(
        'add_meeting',
        '/meetings/add',
        factory=meeting_factory
    )
    config.add_view(
        add_or_edit_group_view,
        route_name='add_meeting',
        renderer='templates/form.pt',
        xhr=False
    )
    config.add_view(
        add_or_edit_group_view,
        route_name='add_meeting',
        renderer='json',
        request_method='POST',
        xhr=True
    )

    # view for single person
    config.add_route(
        'person',
        '/person/{id}',
        factory=person_factory,
    )
    config.add_view(
        person_view,
        route_name='person',
        renderer='templates/person.pt',
    )

    config.add_route(
        'download_document',
        '/media/assets/{consultation_doc_id}',
        factory=consultation_document_factory
    )
    config.add_view(
        download_consultation_document,
        request_method='GET',
        route_name='download_document'
    )
