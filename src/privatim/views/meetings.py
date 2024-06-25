from markupsafe import Markup, escape
from pyramid.response import Response
from privatim.reporting.report import (
    MeetingReport,
    ReportOptions,
    HTMLReportRenderer,
)
from privatim.utils import datetime_format
from privatim.controls.controls import Button, Icon, IconStyle
from pyramid.httpexceptions import (
    HTTPFound,
    HTTPNotFound,
    HTTPBadRequest,
    HTTPMethodNotAllowed,
)
from privatim.utils import maybe_escape
from sqlalchemy import select

from privatim.utils import fix_utc_to_local_time
from privatim.forms.meeting_form import MeetingForm
from privatim.models import Meeting, User, WorkingGroup
from privatim.i18n import _
from privatim.i18n import translate

from typing import TypeVar, TYPE_CHECKING, Any, Sequence

if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from sqlalchemy.orm import Query
    from privatim.types import RenderData, XHRDataOrRedirect
    _Q = TypeVar("_Q", bound=Query[Any])
    from privatim.types import MixedDataOrRedirect


def meeting_view(
        context: Meeting,
        request: 'IRequest'
) -> 'RenderData':
    """ Displays a single meeting. """

    assert isinstance(context, Meeting)
    formatted_time = datetime_format(context.time)

    request.add_action_menu_entry(
        translate(_('Export meeting protocol')),
        request.route_url('export_meeting_as_pdf_view', id=context.id),
    )
    request.add_action_menu_entry(
        translate(_('Delete Meeting')),
        request.route_url('delete_meeting', id=context.id),
    )

    # should already be sorted, (by 'order_by')
    assert context.agenda_items == sorted(
        context.agenda_items, key=lambda x: x.position
    ), "Agenda items are not sorted"

    agenda_items = []
    for item in context.agenda_items:
        agenda_items.append(
            {
                'title': item.title,
                'description': item.description,
                'id': item.id,
                'position': item.position,
                'edit_btn': Button(
                    url=request.route_url('edit_agenda_item', id=item.id),
                    icon='edit',
                    description=_('Edit Agenda Item'),
                    css_class='',
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
    title = translate(_('Attendees'))
    return {
        'time': formatted_time,
        'meeting': context,
        'meeting_attendees': get_generic_user_list(
            request, context.attendees, title
        ),
        'agenda_items': agenda_items,
        'sortable_url': data_sortable_url,
    }


def meeting_buttons(
    meeting: Meeting, request: 'IRequest'
) -> list[Button]:

    return [
        Button(
            title=_('Details'),
            url=request.route_url('meeting', id=meeting.id),
            css_class='btn-sm btn-secondary'
        ),
        Button(
            url=(
                request.route_url(
                    'edit_meeting', meeting_id=meeting.id
                )
            ),
            icon='edit',
            description=_('Edit Meeting'),
            css_class='btn-sm btn-secondary disabled',   # Edit disabled for
            # now, not all fields are quite ready for editing
            modal='#edit-xhr',
        ),
        Button(
            url=(
                request.route_url(
                    'delete_meeting', id=meeting.id
                )
            ),
            icon='trash',
            description=_('Delete'),
            css_class='btn-sm btn-danger',
            modal='#delete-xhr',
            data_item_title=meeting.name,  # set's the name in "Do you really
            # wish to delete ${name}?" message
        )
    ]


def get_generic_user_list(
    request: 'IRequest',
    users: Sequence[User],
    title: str
) -> Markup:
    """Returns an HTML list of users with links to their profiles """
    user_items = tuple(
        Markup(
            '<li class="user-list-item">{} '
            '<a href="{}" class="mb-1">{}</a>'
            '</li>'
        ).format(
            Icon('user', IconStyle.solid),
            request.route_url("person", id=user.id),
            escape(user.fullname)
        )
        for user in users
    )
    return Markup(
        '''
    <div class="generic-user-list-container">
        <p>
            <span class="fw-bold">{}:</span>
        </p>
        <ul class="generic-user-list">{}</ul>
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
    response.content_disposition = f'inline;filename={report.filename}'
    return response


# alias working_group_view
def meetings_view(
        context: WorkingGroup,
        request: 'IRequest'
) -> 'RenderData':
    """ Displays the table of meetings a single working group has. """

    assert isinstance(context, WorkingGroup)

    request.add_action_menu_entry(
        translate(_('Delete Working Group')),
        request.route_url('delete_working_group', id=context.id)
    )

    add_meeting_link = request.route_url('add_meeting', id=context.id)
    leader = None
    if context.leader is not None:
        leader = Markup(  # noqa: MS001
            '<a href="{}" class="mb-1">{}</a>'.format(
                request.route_url("person", id=context.leader.id),
                context.leader.fullname
            )
        )
    title = translate(_('Participants'))
    return {
        'title': context.name,
        'add_meeting_link': add_meeting_link,
        'leader': leader,
        'user_list': get_generic_user_list(request, context.users, title),
        'meetings': context.meetings,
    }


def add_meeting_view(
        context: WorkingGroup,
        request: 'IRequest'
) -> 'MixedDataOrRedirect':

    assert isinstance(context, WorkingGroup)
    target_url = request.route_url('meetings', id=context.id)  # fallback
    form = MeetingForm(context, request)
    session = request.dbsession

    meeting = None
    if request.method == 'POST' and form.validate():
        stmt = select(User).where(User.id.in_(form.attendees.raw_data))
        attendees = list(session.execute(stmt).scalars().all())
        assert form.time.data is not None
        time = fix_utc_to_local_time(form.time.data)
        meeting = Meeting(
            name=form.name.data,
            time=time,
            attendees=attendees,
            working_group=context
        )
        session.add(meeting)
        message = _(
            'Successfully added meeting "${name}"',
            mapping={'name': form.name.data}
        )
        request.messages.add(message, 'success')

        if request.is_xhr:
            return {'redirect_to': target_url}
        else:
            return HTTPFound(location=target_url)

    if meeting is not None:
        target_url = request.route_url('meeting', id=meeting.id)

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
        context: Meeting,
        request: 'IRequest'
) -> 'MixedDataOrRedirect':

    target_url = request.route_url('meetings', id=context.id)
    form = MeetingForm(context, request)
    session = request.dbsession
    meeting = context

    if request.method == 'POST' and form.validate():
        form.populate_obj(meeting)
        if request.is_xhr:
            data = {
                'name': maybe_escape(meeting.name),
                # 'time': maybe_escape(meeting.time),
            }
            session.flush()
            session.refresh(meeting)
            data['DT_RowId'] = f'row-{meeting.id}'

            data['buttons'] = Markup(' ').join(
                meeting_buttons(meeting, request)
            )

            message = _('Successfully edited meeting "${name}"',
                        mapping={'name': form.name.data})
            data['message'] = translate(message, request.locale_name)
            return data
        else:
            return HTTPFound(location=target_url)
    if request.is_xhr:
        return {'errors': form.errors}
    else:
        return {
            'form': form,
            'target_url': target_url,
            'csrf_token': request.session.get_csrf_token()}


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

    if request.is_xhr:
        return {'success': translate(message, request.locale_name)}

    request.messages.add(message, 'success')
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
