from markupsafe import Markup
from pyramid.httpexceptions import HTTPFound

from privatim.controls import Button
from privatim.data_table import AJAXDataTable, DataColumn, maybe_escape
from sqlalchemy import func, select

from privatim.utils import fix_utc_to_local_time
from privatim.static import xhr_edit_js
from privatim.forms.meeting_form import MeetingForm
from privatim.models import Meeting, User, WorkingGroup
from privatim.i18n import _
from privatim.i18n import translate

from typing import TypeVar, TYPE_CHECKING, Any

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

    # Assuming meeting.time is a datetime object
    formatted_time = context.time.strftime("%d %B %Y, %I:%M %p")
    assert isinstance(context, Meeting)

    items = []
    for item in context.agenda_items:
        items.append({
            'title': item.title,
            'description': item.description,
            'id': item.id,
        })

    return {
        'time': formatted_time,
        'meeting': context,
        'agenda_items': items,
    }


class MeetingTable(AJAXDataTable[Meeting]):
    default_options = {
        'length_menu': [[25, 50, 100, -1], [25, 50, 100, 'All']],
        'order': [[0, 'asc']]  # corresponds to column name
    }

    # format data
    name = DataColumn(title=_('Name'))

    # time = DataColumn(
    #     _('Time'), format_data=lambda d: d.strftime('%m/%d/%Y, %H:%M:%S')
    # )

    def __init__(self, org: WorkingGroup, request: 'IRequest') -> None:
        super().__init__(org, request, id='meeting-table')
        xhr_edit_js.need()
        assert isinstance(self.context, WorkingGroup)

    def apply_static_filters(self, query: '_Q') -> '_Q':
        return query.filter(Meeting.working_group_id == self.context.id)

    def total_records(self) -> int:
        if not hasattr(self, '_total_records'):
            session = self.request.dbsession
            query = session.query(func.count(Meeting.id))
            query = self.apply_static_filters(query)
            self._total_records: int = query.scalar()
        return self._total_records

    def query(self) -> 'Query[Meeting]':
        session = self.request.dbsession
        query = session.query(Meeting)
        query = self.apply_static_filters(query)
        if self.order_by:
            query = query.order_by(
                getattr(getattr(Meeting, self.order_by), self.order_dir)()
            )
        else:
            query = query.order_by(Meeting.name.asc())
        return query

    def buttons(self, meeting: Meeting | None = None) -> list[Button]:
        if meeting is None:
            return []

        assert isinstance(meeting, Meeting)
        return meeting_buttons(meeting,  self.request)


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


def meetings_view(
        context: WorkingGroup,
        request: 'IRequest'
) -> 'RenderData':
    """ Displays the table of meetings a single working group has. """

    assert isinstance(context, WorkingGroup)

    return {
        'group': context,
        'title': f'{context.name}: Sitzungen',
        'meetings': context.meetings,
    }


def add_meeting_view(
        context: WorkingGroup,
        request: 'IRequest'
) -> 'MixedDataOrRedirect':

    assert isinstance(context, WorkingGroup)
    target_url = request.route_url('meetings', id=context.id)

    form = MeetingForm(context, request)
    form.name.data = ''
    session = request.dbsession
    if request.method == 'POST' and form.validate():
        stmt = select(User).where(User.id.in_(form.attendees.raw_data))
        attendees = list(session.execute(stmt).scalars().all())
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
            # link_to_meeting = request.route_url('meeting', id=meeting.id)
            data = {
                'name': meeting.name
                # 'time': meeting.time,
            }

            request.dbsession.flush()
            request.dbsession.refresh(meeting)
            data['DT_RowId'] = f'row-{meeting.id}'

            data['buttons'] = Markup(' ').join(
                meeting_buttons(meeting, request))
            data['message'] = translate(message, request.locale_name)
            return data
        else:
            return HTTPFound(location=target_url)
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
        location=request.route_url('working_groups'),
    )
