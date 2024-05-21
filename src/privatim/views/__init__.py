from typing import TYPE_CHECKING

from pyramid.security import NO_PERMISSION_REQUIRED
from fliestorage_download import download_consultation_document

from privatim.route_factories import agenda_item_factory
from privatim.route_factories import consultation_document_factory
from privatim.route_factories import consultation_factory
from privatim.route_factories import default_meeting_factory
from privatim.route_factories import meeting_factory
from privatim.route_factories import person_factory
from privatim.route_factories import working_group_factory
from privatim.views.activities import activities_view
from privatim.views.agenda_items import add_agenda_item_view
from privatim.views.agenda_items import delete_agenda_item_view
from privatim.views.agenda_items import edit_agenda_item_view
from privatim.views.consultations import add_or_edit_consultation_view
from privatim.views.consultations import consultation_view
from privatim.views.consultations import consultations_view
from privatim.views.forbidden import forbidden_view
from privatim.views.home import home_view
from privatim.views.login import login_view
from privatim.views.logout import logout_view
from privatim.views.meetings import add_meeting_view
from privatim.views.meetings import delete_meeting_view
from privatim.views.meetings import edit_meeting_view
from privatim.views.meetings import meeting_view
from privatim.views.meetings import meetings_view
from privatim.views.password_change import password_change_view
from privatim.views.password_retrieval import password_retrieval_view
from privatim.views.people import people_view, person_view
from privatim.views.working_groups import add_or_edit_group_view
from privatim.views.working_groups import working_groups_view


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
        activities_view,
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
        renderer='templates/activities.pt'
    )

    # working groups overview
    config.add_route('working_groups', '/working_groups')
    config.add_view(
        working_groups_view,
        route_name='working_groups',
        renderer='templates/working_groups.pt',)

    # adding a single working group
    config.add_route(
        'add_working_group',
        '/working_groups/add',
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

    # Note that view working_group is like viewing all meetings (same
    # thing)
    config.add_route(
        'meetings',
        '/working_groups/{id}/meetings/view',
        factory=working_group_factory
    )
    config.add_view(
        meetings_view,
        route_name='meetings',
        renderer='templates/table.pt',
    )

    # Add meeting per working_group
    config.add_route(
        'add_meeting',
        '/working_groups/{id}/add',
        factory=working_group_factory
    )
    config.add_view(
        add_meeting_view,
        route_name='add_meeting',
        renderer='templates/form.pt',
        xhr=False
    )
    config.add_view(
        add_meeting_view,
        route_name='add_meeting',
        renderer='json',
        request_method='POST',
        xhr=True
    )

    # Add meeting per working_group
    config.add_route(
        'edit_meeting',
        '/meetings/{meeting_id}/edit',
        factory=meeting_factory
    )
    config.add_view(
        edit_meeting_view,
        route_name='edit_meeting',
        renderer='templates/form.pt',
        xhr=False
    )
    config.add_view(
        edit_meeting_view,
        route_name='edit_meeting',
        renderer='json',
        request_method='POST',
        xhr=True
    )

    config.add_route(
        'delete_meeting',
        '/meetings/{id}/delete',
        factory=meeting_factory
    )
    config.add_view(
        delete_meeting_view,
        route_name='delete_meeting',
        xhr=False
    )
    config.add_view(
        delete_meeting_view,
        route_name='delete_meeting',
        renderer='json',
        request_method='DELETE',
        xhr=True
    )

    # Agenda items

    config.add_route(
        'add_agenda_item',
        '/meetings/{id}/add',
        factory=meeting_factory
    )
    config.add_view(
        add_agenda_item_view,
        route_name='add_agenda_item',
        renderer='templates/form.pt',
        xhr=False
    )
    config.add_view(
        add_agenda_item_view,
        route_name='add_agenda_item',
        renderer='json',
        request_method='POST',
        xhr=True
    )

    config.add_route(
        'edit_agenda_item',
        '/agenda_items/{id}/edit',
        factory=agenda_item_factory
    )
    config.add_view(
        edit_agenda_item_view,
        route_name='edit_agenda_item',
        renderer='templates/form.pt',
        xhr=False
    )
    config.add_view(
        edit_agenda_item_view,
        route_name='edit_agenda_item',
        renderer='json',
        request_method='POST',
        xhr=True
    )

    config.add_route(
        'delete_agenda_item',
        '/agenda_items/{id}/delete',
        factory=agenda_item_factory
    )
    config.add_view(
        delete_agenda_item_view,
        route_name='delete_agenda_item',
        xhr=False
    )
    config.add_view(
        delete_agenda_item_view,
        route_name='delete_agenda_item',
        renderer='json',
        request_method='DELETE',
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

    # single meeting view
    config.add_route(
        'meeting', '/meeting/{id}', factory=default_meeting_factory)
    config.add_view(
        meeting_view,
        route_name='meeting',
        renderer='templates/meeting.pt'
    )

    config.add_route(
        'password_retrieval',
        '/password_retrieval'
    )
    config.add_view(
        password_retrieval_view,
        route_name='password_retrieval',
        renderer='templates/password_retrieval.pt',
        require_csrf=False,
        request_method=('GET', 'POST'),
        permission=NO_PERMISSION_REQUIRED
    )

    config.add_route(
        'password_change',
        '/password_change'
    )
    config.add_view(
        password_change_view,
        route_name='password_change',
        renderer='templates/password_change.pt',
        request_method=('GET', 'POST'),
        require_csrf=False,
        permission=NO_PERMISSION_REQUIRED
    )
