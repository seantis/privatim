from pytz import timezone
from markupsafe import Markup
from pyramid.httpexceptions import HTTPFound

from privatim.controls.controls import Button
from privatim.utils import maybe_escape
from sqlalchemy import select

from privatim.layouts.layout import DEFAULT_TIMEZONE
from privatim.utils import fix_utc_to_local_time
from privatim.forms.meeting_form import MeetingForm
from privatim.models import Meeting, User, WorkingGroup
from privatim.i18n import _
from privatim.i18n import translate

from typing import TypeVar, TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from sqlalchemy.orm import Query
    from privatim.types import RenderData, XHRDataOrRedirect
    from datetime import datetime
    from pytz import BaseTzInfo
    _Q = TypeVar("_Q", bound=Query[Any])
    from privatim.types import MixedDataOrRedirect


def datetime_format(
        dt: 'datetime',
        format: str = '%d.%m.%y %H:%M',
        tz: 'BaseTzInfo' = DEFAULT_TIMEZONE
) -> str:

    if not dt.tzinfo:
        # If passed datetime does not carry any timezone information, we
        # assume (and force) it to be UTC, as all timestamps should be.
        dt = timezone('UTC').localize(dt)
    return dt.astimezone(tz).strftime(format)


def meeting_view(
        context: Meeting,
        request: 'IRequest'
) -> 'RenderData':
    """ Displays a single meeting. """

    assert isinstance(context, Meeting)
    formatted_time = datetime_format(context.time)

    items = []
    for item in context.agenda_items:
        items.append(
            {
                'title': item.title,
                'description': item.description,
                'id': item.id,
                'edit_btn': Button(
                    url=request.route_url('edit_agenda_item', id=item.id),
                    icon='edit',
                    description=_('Edit Agenda Item'),
                    css_class='',
                ),
            }
        )

    return {
        'time': formatted_time,
        'meeting': context,
        'agenda_items': items,
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
    session = request.dbsession

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
