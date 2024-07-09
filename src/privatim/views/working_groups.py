from pyramid.httpexceptions import HTTPFound

from privatim.forms.working_group_forms import WorkingGroupForm
from sqlalchemy import select, exists
from privatim.models import WorkingGroup, User, Meeting
from privatim.i18n import _, translate


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.types import (RenderData, RenderDataOrRedirect,
                                XHRDataOrRedirect)


def working_groups_view(request: 'IRequest') -> 'RenderData':
    session = request.dbsession
    stmt = select(WorkingGroup).order_by(WorkingGroup.name)
    working_groups = session.scalars(stmt).unique().all()
    return {'working_groups': working_groups}


def add_or_edit_working_group(

    context: WorkingGroup | None, request: 'IRequest'
) -> 'RenderDataOrRedirect':

    if isinstance(context, WorkingGroup):   # edit situation
        group = context
    else:  # add situation
        group = None

    form = WorkingGroupForm(context, request)
    target_url = request.route_url('working_groups')
    session = request.dbsession

    if request.method == 'POST' and form.validate():
        if group is None:

            stmt = select(User).where(User.id.in_(form.members.raw_data))
            users = list(session.execute(stmt).scalars().all())

            leader_id = form.leader.data
            leader_id = None if leader_id == '0' else leader_id
            leader = None
            if leader_id is not None and leader_id != '0':
                leader = session.get(User, leader_id)

            if leader is not None and leader not in users:
                users.append(leader)

            group = WorkingGroup(
                name=form.name.data or '',
                leader=leader,
                users=users
            )
            session.add(group)
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
            'target_url': target_url,
            'title': _('Add Working Group')
        }


def delete_working_group_view(
    context: WorkingGroup, request: 'IRequest'
) -> 'XHRDataOrRedirect':
    assert isinstance(context, WorkingGroup)
    deleted_working_group_name = context.name

    session = request.dbsession
    meetings_exist_stmt = select(
        exists().where(Meeting.working_group_id == context.id)
    )
    meetings_exist = session.execute(meetings_exist_stmt).scalar()

    if meetings_exist:
        warning_message = _(
            'Cannot delete working group "${name}" because it has associated '
            'meetings. Please delete all meetings first.',
            mapping={'name': deleted_working_group_name},
        )

        if request.is_xhr:
            return {'error': translate(warning_message, request.locale_name)}
        request.messages.add(warning_message, 'warning')
        return HTTPFound(location=request.route_url('working_groups'))

    session.delete(context)
    session.flush()
    success_message = _(
        'Successfully deleted working group "${name}"',
        mapping={'name': deleted_working_group_name},
    )

    if request.is_xhr:
        return {'success': translate(success_message, request.locale_name)}
    request.messages.add(success_message, 'success')
    return HTTPFound(location=request.route_url('working_groups'))
