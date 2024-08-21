from pyramid.httpexceptions import HTTPFound
from sqlalchemy.orm import joinedload
from privatim.forms.working_group_forms import WorkingGroupForm
from sqlalchemy import select, exists
from privatim.models import WorkingGroup, User, Meeting
from privatim.i18n import _
from privatim.utils import maybe_escape


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.types import (RenderData, RenderDataOrRedirect,
                                XHRDataOrRedirect)


def working_groups_view(request: 'IRequest') -> 'RenderData':
    return {
        'working_groups': [
            {
                'group': group,
                'users': [
                    {
                        'id': user.id,
                        'fullname': user.fullname,
                        'picture_url': (
                            request.route_url(
                                'download_file', id=user.profile_pic_id
                            )
                            if user.profile_pic_id
                            else request.static_url(
                                'privatim:static/default_profile_icon.png'
                            )
                        ),
                        'profile_url': request.route_url('person', id=user.id),
                    }
                    for user in sorted(
                        group.users, key=lambda user: user.fullname.lower()
                    )
                ],
            }
            for group in request.dbsession.scalars(
                select(WorkingGroup)
                .options(joinedload(WorkingGroup.users))
                .order_by(WorkingGroup.name)
            )
            .unique()
            .all()
        ]
    }


def add_working_group(request: 'IRequest') -> 'RenderDataOrRedirect':
    form = WorkingGroupForm(None, request)
    target_url = request.route_url('working_groups')
    session = request.dbsession
    if request.method == 'POST' and form.validate():
        stmt = select(User).where(User.id.in_(form.users.raw_data or ()))
        users = list(session.execute(stmt).scalars().all())
        leader_id = form.leader.data
        leader_id = None if leader_id == '0' else leader_id
        leader = None

        # Leader is also part of members even if not explicitly set
        if leader_id is not None and leader_id != '0':
            leader = session.get(User, leader_id)
        if leader is not None and leader not in users:
            users.append(leader)

        group = WorkingGroup(
            name=maybe_escape(form.name.data),
            leader=leader,
            users=users,
        )
        if form.chairman.data:
            group.chairman_id = form.chairman.data

        session.add(group)
        message = _(
            'Successfully added working group "${name}"',
            mapping={'name': form.name.data},
        )
        if not request.is_xhr:
            request.messages.add(message, 'success')
        if request.is_xhr:
            return {'redirect_url': target_url}
        else:
            return HTTPFound(location=target_url)
    if request.is_xhr:
        return {'errors': form.errors}
    else:
        return {
            'form': form,
            'target_url': target_url,
            'title': _('Add Working Group'),
        }


def edit_working_group(
    group: WorkingGroup, request: 'IRequest'
) -> 'RenderDataOrRedirect':

    target_url = request.route_url('meetings', id=group.id)
    form = WorkingGroupForm(group, request)
    session = request.dbsession

    if request.method == 'POST' and form.validate():
        group.name = maybe_escape(form.name.data)

        # Update leader
        leader_id = form.leader.data
        leader_id = None if leader_id == '0' else leader_id
        if leader_id is not None and leader_id != '0':
            group.leader = session.get(User, leader_id)
        else:
            group.leader = None

        # Update members
        stmt = select(User).where(User.id.in_(form.users.raw_data or ()))
        users = list(session.execute(stmt).scalars().all())
        if group.leader is not None and group.leader not in users:
            users.append(group.leader)

        group.users = users
        chairman_stmt = select(User).where(
            User.id.in_(form.chairman.data)
        )
        chairman_or_none = session.execute(chairman_stmt).scalar_one_or_none()

        # somehow this does not make chairman display
        if chairman_or_none:
            group.chairman = chairman_or_none

        session.add(group)
        session.flush()

        message = _(
            'Successfully updated working group "${name}"',
            mapping={'name': form.name.data},
        )
        request.messages.add(message, 'success')
        return HTTPFound(location=target_url)

    if request.is_xhr:
        return {'errors': form.errors}
    else:
        return {
            'form': form,
            'target_url': target_url,
            'title': _('Edit Working Group'),
        }


def delete_working_group_view(
    context: WorkingGroup, request: 'IRequest'
) -> 'XHRDataOrRedirect':
    assert isinstance(context, WorkingGroup)
    deleted_working_group_name = context.name
    target_url = request.route_url('working_groups')

    session = request.dbsession
    meetings_exist = session.execute(select(
        exists().where(Meeting.working_group_id == context.id)
    )).scalar()
    if not meetings_exist:
        session.delete(context)
        session.flush()
        msg = _(
            'Successfully deleted working group "${name}"',
            mapping={
                'name': deleted_working_group_name,
            },
        )
        request.messages.add(msg, 'success')
        if request.is_xhr:
            return {
                'success': msg,
                'redirect_url': target_url,
            }
    else:
        warning_message = _(
            'Cannot delete working group "${name}" because it has associated '
            'meetings. Please delete all meetings first.',
            mapping={'name': deleted_working_group_name},
        )
        request.messages.add(warning_message, 'warning')

        if request.is_xhr:
            return {
                'success':  False,
                'redirect_url': request.route_url('working_groups')
            }
    return HTTPFound(location=request.route_url('working_groups'))
