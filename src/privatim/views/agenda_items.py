from pyramid.httpexceptions import HTTPFound
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from privatim.forms.agenda_item_form import AgendaItemForm, AgendaItemCopyForm
from privatim.i18n import _
from privatim.i18n import translate
from privatim.models import (
    AgendaItem,
    AgendaItemDisplayState,
    AgendaItemStatePreference,
)
from privatim.models import Meeting

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.types import MixedDataOrRedirect
    from privatim.types import XHRDataOrRedirect


def add_agenda_item_view(
    context: Meeting,
    request: 'IRequest'
) -> 'MixedDataOrRedirect':

    assert isinstance(context, Meeting)
    target_url = request.route_url('meeting', id=context.id)

    form = AgendaItemForm(context, request)
    session = request.dbsession
    if request.method == 'POST' and form.validate():
        assert form.title.data
        desc = form.description.data if form.description.data else ''
        agenda_item = AgendaItem.create(
            session,
            title=form.title.data,
            description=desc,
            meeting=context
        )
        session.add(agenda_item)
        message = _(
            'Successfully added agend item "${title}"',
            mapping={'title': form.title.data}
        )
        request.messages.add(message, 'success')
        if request.is_xhr:
            data = {
                'name': agenda_item.title
            }

            request.dbsession.flush()
            request.dbsession.refresh(agenda_item)
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


def edit_agenda_item_view(
    context: AgendaItem,
    request: 'IRequest'
) -> 'MixedDataOrRedirect':

    target_url = request.route_url('meeting', id=context.meeting.id)
    form = AgendaItemForm(context, request)
    session = request.dbsession
    agenda_item = context

    if request.method == 'POST' and form.validate():
        form.populate_obj(agenda_item)
        if request.is_xhr:
            data = {
                'name': agenda_item.title,
            }
            session.flush()
            session.refresh(agenda_item)
            message = _(
                'Successfully edited agenda_item "${title}"',
                mapping={'title': form.title.data}
            )
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
            'title': form._title,
            'csrf_token': request.session.get_csrf_token()
        }


def delete_agenda_item_view(
    context: AgendaItem,
    request: 'IRequest'
) -> 'XHRDataOrRedirect':

    assert isinstance(context, AgendaItem)
    title = context.title

    session = request.dbsession
    session.delete(context)
    session.flush()

    message = _(
        'Successfully deleted agena_item "${title}"',
        mapping={'name': title}
    )

    target_url = request.route_url('meeting', id=context.meeting.id)
    if request.is_xhr:
        return {
            'success': translate(message, request.locale_name),
            'name': 'test',
            'redirect_url': target_url
        }

    request.messages.add(message, 'success')
    return HTTPFound(location=target_url)


def copy_agenda_item_view(
    context: Meeting, request: 'IRequest'
) -> 'MixedDataOrRedirect':
    available_meetings: list[Meeting] = [
        meeting for meeting in context.working_group.meetings
        if meeting.id != context.id
    ]
    form = AgendaItemCopyForm(context, request, available_meetings)
    session = request.dbsession
    assert isinstance(context, Meeting)

    target_url = request.route_url('meeting', id=context.id)
    if request.method == 'POST' and form.validate():
        source_meeting_id = form.copy_from.data
        stmt = (
            select(Meeting)
            .where(Meeting.id == source_meeting_id)
            .options(selectinload(Meeting.agenda_items))
        )
        source_meeting = session.execute(stmt).scalar_one()
        # Create deep copies of agenda items from the source meeting to the
        # context meeting
        # Put them in a list, else this will loop forever
        for agenda_item in list(source_meeting.agenda_items):
            new_item = AgendaItem.create(
                session,
                title=agenda_item.title,
                description=(
                    agenda_item.description
                    if form.copy_description.data
                    else ''
                ),
                meeting=context,
            )
            session.add(new_item)

        session.flush()
        message = _(
            'Successfully copied agenda items from "${name}"',
            mapping={'name': source_meeting.name},
        )
        if request.is_xhr:
            return {'success': translate(message, request.locale_name)}
        request.messages.add(message, 'success')
        return HTTPFound(location=target_url)

    return {
        'form': form,
        'title': form._title,
        'target_url': target_url,
    }


def update_single_agenda_item_state(request: 'IRequest') -> dict[str, str]:
    """Update the expanded/collapsed state of a single agenda item for the
    current user"""
    session = request.dbsession
    new_state = AgendaItemDisplayState(int(request.json_body['state']))
    agenda_item_id = request.matchdict['id']

    # Look up existing preference
    preference = session.execute(
        select(AgendaItemStatePreference).where(
            AgendaItemStatePreference.agenda_item_id == agenda_item_id,
            AgendaItemStatePreference.user_id == request.user.id,
        )
    ).scalar_one_or_none()

    if not preference:
        preference = AgendaItemStatePreference(
            user_id=request.user.id,
            agenda_item_id=agenda_item_id,
            state=new_state,
        )
        session.add(preference)
    else:
        preference.state = new_state
        session.add(preference)

    return {'status': 'success'}


def update_bulk_agenda_items_state(
        context: Meeting,
        request: 'IRequest'
) -> dict[str, str | int]:
    """Update the expanded/collapsed state of all agenda items in a meeting
    for the current user"""

    session = request.dbsession
    new_state = AgendaItemDisplayState(int(request.json_body['state']))

    # Get all agenda items for the meeting
    agenda_items = context.agenda_items

    # Update or create preferences for all items
    for agenda_item in agenda_items:
        preference = session.execute(
            select(AgendaItemStatePreference).where(
                AgendaItemStatePreference.agenda_item_id == agenda_item.id,
                AgendaItemStatePreference.user_id == request.user.id,
            )
        ).scalar_one_or_none()

        if not preference:
            preference = AgendaItemStatePreference(
                user_id=request.user.id,
                agenda_item_id=agenda_item.id,
                state=new_state,
            )
        else:
            preference.state = new_state

        session.add(preference)

    return {'status': 'success', 'updated': len(agenda_items)}
