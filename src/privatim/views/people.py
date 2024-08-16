from pyramid.httpexceptions import HTTPFound
from sqlalchemy import nullslast
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select
from markupsafe import Markup

from privatim.forms.user_form import UserForm
from privatim.i18n import _
from privatim.utils import strip_p_tags, maybe_escape
from privatim.models import User, WorkingGroup

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.types import RenderData, RenderDataOrRedirect


def people_view(request: 'IRequest') -> 'RenderData':

    session = request.dbsession
    people = (
        session.execute(
            select(User).order_by(
                nullslast(User.last_name),
                nullslast(User.first_name)
            )
        ).scalars()
    )

    return {
        'title': _('List of Persons'),
        'people': people,
    }


def person_view(context: User, request: 'IRequest') -> 'RenderData':
    session = request.dbsession
    stmt = (
        select(User)
        .options(
            selectinload(User.comments),
            selectinload(User.consultations),
        )
        .filter_by(id=context.id)
    )
    user: User = session.execute(stmt).scalar_one()

    meetings_dict = [
        {
            'name': Markup(strip_p_tags(meeting.name)),
            'url': request.route_url('meeting', id=meeting.id)
        } for meeting in user.meetings
    ]

    consultation_dict = [
        {
            'title': Markup(strip_p_tags(consultation.title)),
            'url': request.route_url('consultation', id=consultation.id)
        } for consultation in user.consultations
    ]

    return {
        'user': user,
        'meeting_urls': meetings_dict,
        'consultation_urls': consultation_dict
    }


def add_user_view(request: 'IRequest') -> 'RenderDataOrRedirect':
    form = UserForm(None, request)

    session = request.dbsession
    target_url = request.route_url('people')

    if request.POST and form.validate():

        stmt = select(WorkingGroup).where(
            WorkingGroup.id.in_(form.groups.raw_data or ())
        )
        user = User(
            email=maybe_escape(form.email.data),
            first_name=maybe_escape(form.first_name.data),
            last_name=maybe_escape(form.last_name.data),
            groups=list(session.execute(stmt).scalars().unique())
        )
        session.add(user)
        session.flush()

        message = _('Successfully added user ${first_name} ${last_name}',
                    mapping={'first_name': user.first_name,
                             'last_name': user.last_name})
        request.messages.add(message, 'success')
        return HTTPFound(target_url)

    return {
        'title': _('Add User'),
        'target_url': target_url,
        'form': form,
    }


def edit_user_view(
    context: User, request: 'IRequest'
) -> 'RenderDataOrRedirect':
    form = UserForm(context, request)
    session = request.dbsession

    if request.method == 'POST' and form.validate():
        form.populate_obj(context)

        session.add(context)
        session.flush()

        message = _('Successfully updated user.')
        request.messages.add(message, 'success')

        if request.is_xhr:
            return {'redirect_to': request.route_url('person', id=context.id)}
        else:
            return HTTPFound(
                location=request.route_url('person', id=context.id)
            )

    if not request.POST:
        form.process(obj=context)
        form.groups.data = [str(group.id) for group in context.groups]

    if request.is_xhr:
        return {'errors': form.errors}
    else:
        return {
            'title': _('Edit User'),
            'form': form,
            'target_url': request.route_url('edit_user', id=context.id),
        }


def delete_user_view(
    context: User, request: 'IRequest'
) -> 'RenderDataOrRedirect':
    session = request.dbsession
    session.delete(context)
    session.flush()

    message = _('Successfully deleted user.')
    request.messages.add(message, 'success')
    return HTTPFound(location=request.route_url('people'))
