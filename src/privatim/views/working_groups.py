from pyramid.httpexceptions import HTTPFound

from privatim.forms.working_group_forms import WorkingGroupForm
from sqlalchemy import select
from privatim.models import Group, WorkingGroup
from privatim.i18n import _


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.types import RenderData, RenderDataOrRedirect


def groups_view(request: 'IRequest') -> 'RenderData':
    session = request.dbsession
    stmt = select(Group).order_by(Group.name)
    groups = session.scalars(stmt).unique()
    return {'groups': groups}


def add_or_edit_group_view(
    context: WorkingGroup | None, request: 'IRequest'
) -> 'RenderDataOrRedirect':

    if isinstance(context, WorkingGroup):   # edit situation
        group = context
    else:  # add situation
        group = None

    form = WorkingGroupForm(context, request)
    target_url = request.route_url('groups')

    if request.method == 'POST' and form.validate():
        if group is None:
            leader_id = form.leader_id.data
            leader_id = None if leader_id == '0' else leader_id
            group = WorkingGroup(
                name=form.name.data or '',
                leader_id=leader_id
            )
            request.dbsession.add(group)
            message = _(
                'Successfully added asset "${name}"',
                mapping={'name': form.name.data}
            )
            if not request.is_xhr:
                request.messages.add(message, 'success')

        form.populate_obj(group)
        if request.is_xhr:
            return {'redirect_to': target_url}
        else:
            return HTTPFound(location=target_url)

    if request.is_xhr:
        return {'errors': form.errors}
    else:
        return {
            'form': form,
            'redirect_after': target_url,
            'title': _('Add Working Group')
        }
