from pyramid.httpexceptions import HTTPFound

from privatim.forms.working_group_forms import WorkingGroupForm
from sqlalchemy import select
from privatim.models import Group, WorkingGroup, User
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
    session = request.dbsession

    if request.method == 'POST' and form.validate():
        if group is None:
            leader_id = form.leader.data
            leader_id = None if leader_id == '0' else leader_id

            stmt = select(User).where(User.id.in_([form.members.data]))
            users = session.execute(stmt).scalars().all()
            group = WorkingGroup(
                name=form.name.data or '',
                leader_id=leader_id,
                users=users
            )
            request.dbsession.add(group)
            message = _(
                'Successfully added working group "${name}"',
                mapping={'name': form.name.data}
            )
            if not request.is_xhr:
                request.messages.add(message, 'success')

        # edit
        # form.populate_obj(group)
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
