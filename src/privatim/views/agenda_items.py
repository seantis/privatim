from pyramid.httpexceptions import HTTPFound

from privatim.data_table import maybe_escape
from privatim.forms.agenda_item_form import AgendaItemForm
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
    from privatim.types import XHRDataOrRedirect

    _Q = TypeVar("_Q", bound=Query[Any])
    from privatim.types import MixedDataOrRedirect


def add_agenda_item_view(
    context: Meeting,
    request: 'IRequest'
) -> 'MixedDataOrRedirect':

    assert isinstance(context, Meeting)
    target_url = request.route_url('meeting', id=context.id)

    form = AgendaItemForm(context, request)
    session = request.dbsession
    if request.method == 'POST' and form.validate():
        agenda_item = AgendaItem(
            title=form.title.data,
            description=form.description.data,
            meeting=context,
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
