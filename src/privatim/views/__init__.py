from typing import TYPE_CHECKING

from pyramid.security import NO_PERMISSION_REQUIRED

from privatim.route_factories import (agenda_item_factory,
                                      general_file_factory, file_factory,
                                      consultation_all_versions_factory)
from privatim.route_factories import consultation_factory
from privatim.route_factories import default_meeting_factory
from privatim.route_factories import meeting_factory
from privatim.route_factories import person_factory
from privatim.route_factories import working_group_factory
from privatim.views.activities import activities_view
from privatim.views.agenda_items import (
    add_agenda_item_view,
    copy_agenda_item_view,
    update_single_agenda_item_state,
    update_bulk_agenda_items_state
)
from privatim.views.agenda_items import delete_agenda_item_view
from privatim.views.agenda_items import edit_agenda_item_view
from privatim.views.consultations import (delete_consultation_view,
                                          add_consultation_view,
                                          edit_consultation_view)
from privatim.views.consultations import consultation_view
from privatim.views.consultations import consultations_view
from privatim.views.general_file import (
    download_general_file_view,
    delete_general_file_view,
)
from privatim.views.forbidden import forbidden_view
from privatim.views.home import home_view, sentry_test_view
from privatim.views.login import login_view
from privatim.views.logout import logout_view
from privatim.views.mtan import mtan_view, mtan_setup_view
from privatim.views.meetings import (
    add_meeting_view,
    export_meeting_as_pdf_view,
    export_meeting_as_docx_view, # Import the new view
    move_agenda_item
)
from privatim.views.meetings import delete_meeting_view
from privatim.views.meetings import edit_meeting_view
from privatim.views.meetings import meeting_view
from privatim.views.meetings import working_group_view
from privatim.views.password_change import password_change_view
from privatim.views.password_retrieval import password_retrieval_view

from privatim.views.people import people_view, person_view, add_user_view, \
    edit_user_view, delete_user_view
from privatim.views.profile import profile_view, add_profile_image_view
from privatim.views.search import search
from privatim.views.trash import trash_view, restore_soft_deleted_model_view
from privatim.views.working_groups import (delete_working_group_view,
                                           add_working_group,
                                           edit_working_group)
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

    config.add_route('mtan', '/mtan')
    config.add_view(
        mtan_view,
        route_name='mtan',
        renderer='templates/mtan.pt',
        require_csrf=False,
        permission=NO_PERMISSION_REQUIRED,
    )

    config.add_route('mtan_setup', '/mtan-setup')
    config.add_view(
        mtan_setup_view,
        route_name='mtan_setup',
        renderer='templates/mtan_setup.pt',
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
        request_method=('GET', 'POST')
    )

    # Adding a new consultation
    config.add_route(
        'add_consultation',
        '/consultations/add',
        factory=consultation_factory
    )
    config.add_view(
        add_consultation_view,
        route_name='add_consultation',
        renderer='templates/form.pt',
        xhr=False
    )
    config.add_view(
        add_consultation_view,
        route_name='add_consultation',
        renderer='json',
        request_method='POST',
        xhr=True
    )

    config.add_route(
        'edit_consultation',
        '/consultations/{id}/edit',
        factory=consultation_factory
    )
    config.add_view(
        edit_consultation_view,
        route_name='edit_consultation',
        renderer='templates/form.pt',
        xhr=False
    )
    config.add_view(
        edit_consultation_view,
        route_name='edit_consultation',
        renderer='json',
        request_method='POST',
        xhr=True
    )

    config.add_route(
        'delete_consultation',
        '/consultations/{id}/delete',
        factory=consultation_factory
    )
    config.add_view(
        delete_consultation_view,
        route_name='delete_consultation',
        xhr=False
    )
    config.add_view(
        delete_consultation_view,
        renderer='json',
        route_name='delete_consultation',
        request_method='DELETE',
        xhr=True
    )

    # view for single consultation
    config.add_route(
        'consultation',
        '/consultation/{id}',
        factory=consultation_all_versions_factory
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
    config.add_route('add_user', '/people/add')
    config.add_view(
        add_user_view,
        route_name='add_user',
        renderer='templates/form.pt',
    )
    config.add_route(
        'edit_user',
        '/person/{id}/edit',
        factory=person_factory
    )
    config.add_view(
        edit_user_view,
        route_name='edit_user',
        renderer='templates/form.pt',
        xhr=False
    )
    config.add_view(
        edit_user_view,
        route_name='edit_user',
        renderer='json',
        request_method='POST',
        xhr=True
    )

    config.add_route(
        'delete_user',
        '/person/{id}/delete',
        factory=person_factory
    )
    config.add_view(
        delete_user_view,
        route_name='delete_user',
        request_method='DELETE',
        xhr=False
    )
    config.add_view(
        delete_user_view,
        route_name='delete_user',
        renderer='json',
        request_method='DELETE',
        xhr=True
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

    # adding a single working group
    config.add_route(
        'add_working_group',
        '/working_groups/add',
    )
    config.add_view(
        add_working_group,
        route_name='add_working_group',
        renderer='templates/form.pt',
        xhr=False
    )
    config.add_view(
        add_working_group,
        route_name='add_working_group',
        renderer='json',
        request_method='POST',
        xhr=True
    )

    config.add_route(
        'edit_working_group',
        '/working_groups/edit/{id}',
        factory=working_group_factory
    )
    config.add_view(
        edit_working_group,
        route_name='edit_working_group',
        renderer='templates/form.pt',
        xhr=False
    )
    config.add_view(
        edit_working_group,
        route_name='edit_working_group',
        renderer='json',
        request_method='POST',
        xhr=True
    )

    # viewing a working_group is like viewing all meetings (same thing)
    config.add_route(
        'meetings',
        '/working_groups/{id}/meetings/',
        factory=working_group_factory
    )
    config.add_view(
        working_group_view,
        route_name='meetings',
        renderer='templates/working_group.pt',
    )

    # Delete working group
    config.add_route(
        'delete_working_group',
        '/working_groups/{id}/delete',
        factory=working_group_factory
    )
    config.add_view(
        delete_working_group_view,
        route_name='delete_working_group',
        xhr=False
    )
    config.add_view(
        delete_working_group_view,
        route_name='delete_working_group',
        renderer='json',
        request_method='DELETE',
        xhr=True
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
        '/meetings/{id}/edit',
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
    # download the meeting report
    config.add_route(
        'export_meeting_as_pdf_view',
        '/meetings/{id}/export',
        factory=meeting_factory
    )
    config.add_view(
        export_meeting_as_pdf_view,
        route_name='export_meeting_as_pdf_view',
        request_method='GET',
    )
    # download the meeting report as DOCX
    config.add_route(
        'export_meeting_as_docx_view',
        '/meetings/{id}/export/docx',
        factory=meeting_factory
    )
    config.add_view(
        export_meeting_as_docx_view,
        route_name='export_meeting_as_docx_view',
        request_method='GET',
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

    config.add_route(
        'copy_agenda_item',
        '/meetings/{id}/copy_agenda_item',
        factory=meeting_factory
    )
    config.add_view(
        copy_agenda_item_view,
        route_name='copy_agenda_item',
        renderer='templates/form.pt',
        xhr=False
    )
    config.add_view(
        copy_agenda_item_view,
        route_name='copy_agenda_item',
        renderer='json',
        request_method='POST',
        xhr=True
    )

    config.add_route(
        'update_single_agenda_item_state,',
        '/agenda_items/{id}/state',
        factory=agenda_item_factory
    )
    config.add_view(
        update_single_agenda_item_state,
        route_name='update_single_agenda_item_state,',
        renderer='json',
        request_method='POST',
        xhr=False
    )
    config.add_view(
        update_single_agenda_item_state,
        route_name='update_single_agenda_item_state,',
        renderer='json',
        request_method='POST',
        xhr=True
    )

    config.add_route(
        'update_bulk_agenda_items_state',
        '/meeting/{id}/agenda_items/bulk/state',
        factory=meeting_factory
    )
    config.add_view(
        update_bulk_agenda_items_state,
        route_name='update_bulk_agenda_items_state',
        renderer='json',
        request_method='POST',
        xhr=False
    )
    config.add_view(
        update_bulk_agenda_items_state,
        route_name='update_bulk_agenda_items_state',
        renderer='json',
        request_method='POST',
        xhr=True
    )

    config.add_route(
        'sortable_agenda_items',
        '/meetings/agenda_items/{id}/move/{subject_id}/{direction}/{'
        'target_id}',
        factory=meeting_factory
    )
    config.add_view(
        move_agenda_item,
        route_name='sortable_agenda_items',
        request_method='POST',
        xhr=False
    )
    config.add_view(
        move_agenda_item,
        route_name='sortable_agenda_items',
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

    # single meeting view
    config.add_route(
        'meeting', '/meeting/{id}',
        factory=default_meeting_factory
    )
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

    config.add_route(
        'profile',
        '/profile'
    )
    config.add_view(
        profile_view,
        route_name='profile',
        request_method='GET',
        renderer='templates/profile.pt'
    )

    config.add_route('add_profile_image', '/profile/add_image')
    config.add_view(
        add_profile_image_view,
        route_name='add_profile_image',
        renderer='json',
        request_method='POST',
        xhr=False,
    )

    # General file
    config.add_route(
        'download_file',
        '/download/file/{id}',
        file_factory,
    )
    config.add_view(
        download_general_file_view,
        route_name='download_file',
        request_method='GET',
    )

    config.add_route(
        'delete_general_file',
        '/delete/file/{id}',
        general_file_factory,
    )
    config.add_view(
        delete_general_file_view,
        route_name='delete_general_file',
        request_param='target_url'
    )
    config.add_view(
        delete_general_file_view,
        route_name='delete_general_file',
        renderer='json',
        request_method='DELETE',
        xhr=True,
        request_param='target_url'
    )

    config.add_route('search', '/search')
    config.add_view(
        search,
        route_name='search',
        renderer='templates/search_results.pt',
    )

    config.add_route('trash', '/trash')
    config.add_view(
        trash_view,
        route_name='trash',
        renderer='templates/trash.pt',
    )

    config.add_route(
        'restore_soft_deleted_model', '/restore/{item_type}/{item_id}'
    )
    config.add_view(
        restore_soft_deleted_model_view,
        route_name='restore_soft_deleted_model',
    )

    config.add_route('testsentry', '/testsentry')
    config.add_view(
        sentry_test_view,
        route_name='testsentry',
        renderer='json',
        require_csrf=False,
        permission=NO_PERMISSION_REQUIRED,
    )
