from pyramid.httpexceptions import HTTPFound
from sqlalchemy import select

from privatim.utils import maybe_escape
from privatim.forms.agenda_item_form import AgendaItemForm, AgendaItemCopyForm
from privatim.i18n import _
from privatim.i18n import translate
from privatim.models import AgendaItem
from privatim.models import Meeting

from typing import TypeVar
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from sqlalchemy.orm import Query
    from privatim.types import MixedDataOrRedirect
    from privatim.types import XHRDataOrRedirect

    _Q = TypeVar("_Q", bound=Query[Any])


def add_agenda_item_view(
    context: Meeting,
    request: 'IRequest'
) -> 'MixedDataOrRedirect':

    assert isinstance(context, Meeting)
    target_url = request.route_url('meeting', id=context.id)

    form = AgendaItemForm(context, request)
    session = request.dbsession
    if request.method == 'POST' and form.validate():
        agenda_item = AgendaItem.create(
            session,
            title=maybe_escape(form.title.data),
            description=maybe_escape(form.description.data),
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
                'name': maybe_escape(agenda_item.title),
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
    meeting = context.meeting

    session = request.dbsession
    session.delete(context)
    session.flush()

    message = _(
        'Successfully deleted agena_item "${title}"',
        mapping={'name': title}
    )

    if request.is_xhr:
        return {'success': translate(message, request.locale_name)}

    request.messages.add(message, 'success')
    return HTTPFound(
        location=request.route_url('meeting', id=meeting.id),
    )


def copy_agenda_item_view(
        context: Meeting,
        request: 'IRequest'
) -> 'MixedDataOrRedirect':

    form = AgendaItemCopyForm(context, request)
    session = request.dbsession
    assert isinstance(context, Meeting)

    target_url = request.route_url('meeting', id=context.id)
    if request.method == 'POST' and form.validate():
        destination_str_id = form.copy_to.data
        stmt = select(Meeting).where(Meeting.id == destination_str_id)
        dest_meeting = session.execute(stmt).scalar_one()

        # Create deep copies of agenda items
        for agenda_item in context.agenda_items:
            new_item = AgendaItem(
                title=agenda_item.title,
                description=agenda_item.description,
                meeting=agenda_item.meeting,
                position=agenda_item.position
            )
            dest_meeting.agenda_items.append(new_item)
        session.add(dest_meeting)
        session.flush()

        message = _(
            'Successfully copied agenda item "${name}"',
            mapping={'name': dest_meeting.name}
        )
        if request.is_xhr:
            return {'success': translate(message, request.locale_name)}
        request.messages.add(message, 'success')
        return HTTPFound(
            location=request.route_url('meeting', id=dest_meeting.id),
        )

    return {
        'form': form,
        'title': form._title,
        'target_url': target_url,
    }
