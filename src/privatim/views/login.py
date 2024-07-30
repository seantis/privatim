from typing import TYPE_CHECKING

from pyramid.httpexceptions import HTTPFound
from pyramid.security import remember
from pyramid.settings import asbool
from sedate import utcnow
from sqlalchemy import select
from sqlalchemy.orm import object_session
from wtforms import Form
from wtforms import PasswordField
from wtforms import StringField
from wtforms import validators

from privatim.i18n import _
from privatim.i18n import translate
from privatim.models import User
from privatim.mtan_tool import MTanTool
from privatim.sms.interfaces import ISMSGateway

if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.types import RenderDataOrRedirect


class LoginForm(Form):

    email = StringField(
        label='Email',
        validators=[
            validators.DataRequired(),
            validators.Email()
        ]
    )

    password = PasswordField(
        label='Passwort',
        validators=[
            validators.DataRequired()
        ]
    )


def login_view(request: 'IRequest') -> 'RenderDataOrRedirect':

    form = LoginForm(request.POST)
    if request.method == 'POST' and form.validate():
        login = form.email.data
        password = form.password.data
        assert login is not None and password is not None

        session = request.dbsession
        stmt = select(User).filter(
            User.email.ilike(login)
        )
        user = session.execute(stmt).scalar_one_or_none()
        if user and user.check_password(password):
            settings = request.registry.settings
            if not asbool(settings.get('auth.password_only', True)):
                if user.mobile_number is None:
                    # start mTAN setup
                    request.session['mtan_setup_user'] = user.id
                    return HTTPFound(location=request.route_url('mtan_setup'))

                # send mTAN and redirect to mTAN view
                request.session['mtan_user'] = user.id

                mtan_tool = MTanTool(session)
                tan = mtan_tool.create_tan(
                    user, request.remote_addr or '0.0.0.0'  # nosec
                )

                content = _(
                    'Privatim Login Token:\n${tan}',
                    mapping={'tan': tan}
                )
                locale = request.locale_name
                gateway = request.registry.getUtility(ISMSGateway)
                gateway.send(
                    receivers=[user.mobile_number],
                    content=translate(content, locale),
                    sender='Privatim'
                )
                return HTTPFound(location=request.route_url('mtan'))

            next_url = request.route_url('home')
            user.last_login = utcnow()
            headers = remember(request, user.id)
            assert object_session(user)
            return HTTPFound(location=next_url, headers=headers)

        # FIXME: log failure for fail2ban
        request.messages.add(_('Login failed.'), 'error')

    return {'form': form}
