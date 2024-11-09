import logging

from markupsafe import Markup
from pyramid.response import Response

from privatim.models.association_tables import AttendanceStatus
from privatim.reporting.report import (
    MeetingReport,
    ReportOptions,
    HTMLReportRenderer,
)
from privatim.utils import datetime_format
from privatim.controls.controls import Button
from pyramid.httpexceptions import (
    HTTPFound,
    HTTPNotFound,
    HTTPBadRequest,
    HTTPMethodNotAllowed,
)
from privatim.utils import fix_utc_to_local_time
from privatim.forms.meeting_form import (
    MeetingForm,
    sync_meeting_attendance_records,
)
from privatim.models import Meeting, WorkingGroup
from privatim.i18n import _
from privatim.i18n import translate

from typing import TypeVar, TYPE_CHECKING, Any, Sequence

if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.models.association_tables import MeetingUserAttendance
    from sqlalchemy.orm import Query
    from privatim.types import RenderData, XHRDataOrRedirect
    _Q = TypeVar("_Q", bound=Query[Any])
    from privatim.types import MixedDataOrRedirect


log = logging.getLogger('privatim.views')


def meeting_view(
        context: Meeting,
        request: 'IRequest'
) -> 'RenderData':
    """ Displays a single meeting. """
    assert isinstance(context, Meeting)
    formatted_time = datetime_format(context.time)
    request.add_action_menu_entries(
        (
            Button(
                url=request.route_url('edit_meeting', id=context.id),
                icon='edit',
                title=_('Edit'),
                css_class='dropdown-item',
                description=_('Edit meeting'),
            ),
            Button(
                title=_('Copy'),
                css_class='dropdown-item',
                url=request.route_url('copy_agenda_item', id=context.id),
                icon='copy',
                description=translate(_('Copy Agenda Items')),
            ),
            Button(
                title=_('Export'),
                css_class='dropdown-item',
                url=request.route_url(
                    'export_meeting_as_pdf_view', id=context.id
                ),
                icon='file-export',
                description=translate(_('Export meeting protocol')),
            ),
            Button(
                url=request.route_url('delete_meeting', id=context.id),
                icon='trash',
                title=_('Delete'),
                css_class='dropdown-item',
                description=_('Delete Meeting'),
                modal='#delete-xhr',
                data_item_title=context.name,
            ),
        )
    )

    agenda_items = []
    for indx, item in enumerate(context.agenda_items, start=1):
        agenda_items.append(
            {
                'title': Markup(
                    '<strong>{}.</strong> {}'.format(
                        indx, Markup.escape(item.title)
                    )
                ),
                'description': Markup(item.description),
                'id': item.id,
                'position': item.position,
                'edit_btn': Button(
                    url=request.route_url('edit_agenda_item', id=item.id),
                    icon='edit',
                    description=_('Edit Agenda Item'),
                ),
                'delete_btn': Button(
                    url=request.route_url('delete_agenda_item', id=item.id),
                    icon='trash',
                    description=_('Delete Agenda Item'),
                    modal='#delete-xhr',
                    data_item_title=item.title,
                ),
            }
        )
    data_sortable_url = request.route_url(
        'sortable_agenda_items',
        id=context.id,
        subject_id='{subject_id}',
        direction='{direction}',
        target_id='{target_id}',
    )
    return {
        'delete_title': _('Delete'),
        'time': formatted_time,
        'meeting': context,
        'meeting_attendees': user_list(
            request, context.attendance_records, translate(_('Members'))
        ),
        'agenda_items': agenda_items,
        'sortable_url': data_sortable_url,
        'navigate_back_up': request.route_url(
            'meetings', id=context.working_group.id
        ),
        'expand_all_text': _('Expand All'),
        'collapse_all_text': _('Collapse All'),
    }


def user_list(
    request: 'IRequest', users: Sequence['MeetingUserAttendance'], title: str
) -> Markup:
    """ Returns an HTML list of users with profile pictures, links to their
    profiles, and checkbox on the right, with tooltips."""
    if not users:
        return Markup('')
    user_items = tuple(
        Markup(
            '<li class="user-list-item d-flex justify-content-between '
            'align-items-center">'
            '<div class="d-flex align-items-center">'
            '<div class="profile-pic-container me-2" style="'
            'width: 24px; height: 24px; overflow: hidden; border-radius: 50%; '
            'display: flex; justify-content: center; align-items: center;">'
            '<img src="{}" alt="{} profile picture" style="'
            'width: 100%; height: 100%; object-fit: cover;">'
            '</div>'
            '<a href="{}" class="mb-1 text-decoration-none">{}</a>'
            '</div>'
            '<div class="form-check" data-bs-toggle="tooltip" title="{}">'
            '<input class="form-check-input fix-checkbox-in-list" '
            'type="checkbox" '
            'value="" '
            'id="attendance-{}" {} disabled>'
            '<label class="form-check-label" for="attendance-{}"></label>'
            '</div>'
            '</li>'
        ).format(
            user.user.profile_pic_download_link(
                request
            ),
            user.user.fullname,
            request.route_url("person", id=user.user_id),
            user.user.fullname,
            (
                translate(_('Attended'))
                if user.status == AttendanceStatus.ATTENDED
                else translate(_('Invited'))
            ),
            user.user_id,
            'checked' if user.status == AttendanceStatus.ATTENDED else '',
            user.user_id,
        )
        for user in sorted(users, key=lambda user: user.user.fullname)
    )
    return Markup(
        '''
    <div class="generic-user-list-container">
        <p>
            <span class="fw-bold">{}:</span>
        </p>
        <ul class="generic-user-list list-unstyled">{}</ul>
    </div>
    '''
    ).format(title, Markup('').join(user_items))


def export_meeting_as_pdf_view(
        context: Meeting, request: 'IRequest',
) -> Response:
    session = request.dbsession
    meeting_id = context.id
    meeting = session.get(Meeting, meeting_id)
    if meeting is None:
        return HTTPNotFound()

    renderer = HTMLReportRenderer()
    options = ReportOptions(language=request.locale_name)
    report = MeetingReport(request, meeting, options, renderer).build()

    response = Response(report.data)
    response.content_type = 'application/pdf'
    name = translate(_('Meeting Report'))
    safe_filename = name + '.pdf'
    response.content_disposition = f'attachment; filename="{safe_filename}"'
    log.info(f'Content-Disposition: {response.content_disposition}')
    return response


def working_group_view(
    context: WorkingGroup, request: 'IRequest'
) -> 'RenderData':
    """Displays the table of meetings a single working group has."""

    assert isinstance(context, WorkingGroup)
    request.add_action_menu_entries(
        (
            Button(
                url=request.route_url('edit_working_group', id=context.id),
                icon='edit',
                title=_('Edit'),
                description=_('Edit Working Group'),
                css_class='dropdown-item',
            ),
            Button(
                url=request.route_url('delete_working_group', id=context.id),
                icon='trash',
                title=_('Delete'),
                description=_('Delete Working Group'),
                css_class='dropdown-item',
                modal='#delete-xhr',
                data_item_title=context.name,
            ),
        )
    )

    chairman = context.chairman
    base_dict = {
        'title': context.name,
        'users': [
            {
                'profile_pic': user.profile_pic_download_link(request),
                'fullname': user.fullname,
                'url': request.route_url("person", id=user.id),
            } for user in sorted(context.users, key=lambda user: user.fullname)
        ],
        'participants': translate(_('Participants')),
        'delete_title': _('Delete Working Group'),
        'leader': context.leader or '',
        'leader_link': request.route_url('person', id=context.leader_id),
        'chairman': chairman,
        'add_meeting_link': request.route_url('add_meeting', id=context.id),
        'navigate_back_up': request.route_url('working_groups'),
        'meetings': context.meetings,
        'request': request
    }

    chairman_dict = {}
    if chairman is not None:
        chairman_dict = {
            'chairman_profile': chairman.profile_pic_download_link(request),
            'chairman_fullname': chairman.fullname,
            'chairman_link': request.route_url('person', id=chairman.id),
        }
    return {**base_dict, **chairman_dict}


def add_meeting_view(
        context: WorkingGroup,
        request: 'IRequest'
) -> 'MixedDataOrRedirect':

    assert isinstance(context, WorkingGroup)
    form = MeetingForm(context, request)
    session = request.dbsession

    target_url = request.route_url('meetings', id=context.id)
    if request.method == 'POST' and form.validate():
        assert form.name.data
        assert form.time.data
        time = fix_utc_to_local_time(form.time.data)

        meeting = Meeting(
            name=form.name.data,
            time=time,
            attendees=[],  # sync_meeting_attendance_records will handle this
            working_group=context,
            creator=request.user
        )

        # XXX A pragmatic shortcut that holds up, for the time being.
        #
        # In the frontend, we are displaying just attendees, it looks like a
        # list uf users, but it's actually stored in `MeetingUserAttendance`.
        # This creates a sort of inconsistency, which is why the lines below
        # are necessary.
        form_attendees = set(form.attendees.data or [])
        working_group_attendees = {str(user.id) for user in context.users}
        # As per requirements, the users of the working group always attend
        # the meeting by default.
        form.attendees.data = list(form_attendees | working_group_attendees)
        sync_meeting_attendance_records(form, meeting, request.POST, session)

        session.add(meeting)
        session.flush()
        message = _(
            'Successfully added meeting "${name}"',
            mapping={'name': form.name.data}
        )
        request.messages.add(message, 'success')
        return HTTPFound(
            location=request.route_url('meeting', id=meeting.id),
        )

    if request.is_xhr:
        return {'errors': form.errors}
    else:
        return {
            'form': form,
            'title': form._title,
            'target_url': target_url,
            'csrf_token': request.session.get_csrf_token()
        }


def edit_meeting_view(
        meeting: Meeting,
        request: 'IRequest'
) -> 'MixedDataOrRedirect':

    assert isinstance(meeting, Meeting)

    target_url = request.route_url('meeting', id=meeting.id)
    form = MeetingForm(meeting, request)
    session = request.dbsession

    if request.method == 'POST' and form.validate():
        form.populate_obj(meeting)
        assert form.time.data is not None
        meeting.name = meeting.name

        meeting.time = fix_utc_to_local_time(form.time.data)

        session.add(meeting)
        session.flush()
        message = _('Successfully edited meeting.')
        if not request.is_xhr:
            request.messages.add(message, 'success')
        return HTTPFound(location=request.route_url('meeting', id=meeting.id))

    return {
        'form': form,
        'target_url': target_url,
        'title': form._title,
    }


def delete_meeting_view(
        context: Meeting,
        request: 'IRequest'
) -> 'XHRDataOrRedirect':

    assert isinstance(context, Meeting)
    name = context.name
    working_group_id = context.working_group.id

    session = request.dbsession
    session.delete(context)
    session.flush()

    message = _(
        'Successfully deleted meeting "${name}"',
        mapping={'name': name}
    )

    request.messages.add(message, 'success')
    if request.is_xhr:
        return {
            'success': translate(message, request.locale_name),
            'redirect_url': request.route_url('meetings', id=working_group_id),
        }

    return HTTPFound(
        location=request.route_url('meetings', id=working_group_id),
    )


def sortable_agenda_items_view(
        context: Meeting, request: 'IRequest'
) -> 'RenderData':

    try:
        subject_id = int(request.matchdict['subject_id'])
        direction = request.matchdict['direction']
        target_id = int(request.matchdict['target_id'])
    except (ValueError, KeyError) as e:
        raise HTTPBadRequest('Request parameters are missing or invalid') \
            from e

    agenda_items = context.agenda_items
    subject_item = next(
        (item for item in agenda_items if item.position == subject_id), None
    )
    target_item = next(
        (item for item in agenda_items if item.position == target_id), None
    )

    if subject_item is None or target_item is None:
        raise HTTPMethodNotAllowed('Invalid subject or target id')

    if direction not in ['above', 'below']:
        raise HTTPMethodNotAllowed('Invalid direction')

    new_position = target_item.position
    if direction == 'below':
        new_position += 1

    for item in agenda_items:
        match direction:
            case 'above' if (new_position
                             <= item.position < subject_item.position):
                item.position += 1
            case 'below' if (subject_item.position
                             < item.position <= new_position):
                item.position -= 1

    subject_item.position = new_position

    return {
        'status': 'success',
        'subject_id': subject_id,
        'direction': direction,
        'target_id': target_id,
    }
