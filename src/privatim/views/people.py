from pyramid.httpexceptions import HTTPFound
from sqlalchemy import nullslast
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select
from markupsafe import Markup
import logging

from privatim.controls.controls import Button
from privatim.forms.user_form import UserForm
from privatim.i18n import _, translate
from privatim.security_policy import PasswordException
from privatim.utils import strip_p_tags, maybe_escape
from privatim.models import User, WorkingGroup
from privatim.views.password_retrieval import mail_retrieval


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.types import RenderData, RenderDataOrRedirect


logger = logging.getLogger('privatim.people')


def user_buttons(
        user: User, request: 'IRequest'
) -> list[Button]:
    return [
        Button(
            url=request.route_url('edit_user', id=user.id),
            icon='edit',
            description=_('Edit user'),
            css_class='btn-sm btn-secondary',
        ),
        Button(
            url=request.route_url('delete_user', id=user.id),
            icon='trash',
            description=_('Delete'),
            css_class='btn-sm btn-outline-danger',
            modal='#delete-xhr',
            data_item_title=_('User ${name}', mapping={'name': user.fullname})
        )
    ]


def people_view(request: 'IRequest') -> 'RenderData':
    session = request.dbsession
    stmt = select(User).order_by(
        nullslast(User.last_name),
        nullslast(User.first_name)
    )
    users = session.execute(stmt).scalars().all()

    people_data = []
    for user in users:
        buttons = user_buttons(user, request)
        button_html = Markup('').join(Markup(button()) for button in buttons)
        people_data.append({
            'id': user.id,
            'name': f'{user.first_name} {user.last_name}',
            'download_link': user.profile_pic_download_link(request),
            'url': request.route_url('person', id=user.id),
            'buttons': button_html
        })

    return {
        'delete_title': _('Delete User'),
        'title': _('List of Persons'),
        'people': people_data,
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
        'profile_pic_url': user.profile_pic_download_link(request),
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
        tags = maybe_escape(form.abbrev.data)
        user = User(
            email=maybe_escape(form.email.data),
            first_name=maybe_escape(form.first_name.data),
            last_name=maybe_escape(form.last_name.data),
            abbrev=tags if tags else '',
            groups=list(session.execute(stmt).scalars().unique())
        )
        user.generate_profile_picture(session)
        session.add(user)
        session.flush()

        try:
            mail_retrieval(user.email, request)
            logger.info(f'Password retrieval mail sent to "{user.email}"')
        except PasswordException as e:
            logger.warning(
                f'[{request.client_addr}] password retrieval: {str(e)}'
            )
        message = _(
            'Successfully added user ${first_name} ${last_name}.'
            'An email has been sent to the requested account with further '
            'information.',
            mapping={
                'first_name': user.first_name,
                'last_name': user.last_name,
            },
        )

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
    target_url = request.route_url('people')

    if request.method == 'POST' and form.validate():
        form.populate_obj(context)

        session.add(context)
        session.flush()

        message = _('Successfully updated user.')
        request.messages.add(message, 'success')

        if request.is_xhr:
            return {'redirect_url': target_url}
        else:
            return HTTPFound(
                location=target_url
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
            'target_url': request.route_url('people'),
        }


def delete_user_view(
    user: User, request: 'IRequest'
) -> 'RenderDataOrRedirect':
    session = request.dbsession
    session.delete(user)
    session.flush()

    full_name = f'{user.first_name} {user.last_name}'
    message = _(
        'Successfully deleted user: {full_name}.',
        mapping={'full_name': full_name}
    )
    request.messages.add(translate(message, request.locale_name), 'success')

    if request.is_xhr:
        return {
            'success': translate(message, request.locale_name),
            'redirect_url': request.route_url('people'),
        }
    else:
        return HTTPFound(location=request.route_url('people'))
