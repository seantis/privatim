from datetime import timezone
from typing import TYPE_CHECKING

from pyramid.httpexceptions import HTTPFound
from pyramid.security import remember
from privatim.i18n import _
from sqlalchemy import select
from wtforms import Form
from wtforms import PasswordField
from wtforms import StringField
from wtforms import validators

from privatim.models import User

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
            next_url = request.route_url('home')
            from datetime import datetime
            user.last_login = datetime.now(timezone.utc)
            headers = remember(request, user.id)
            from sqlalchemy.orm import object_session
            assert object_session(user)
            return HTTPFound(location=next_url, headers=headers)

        request.messages.add(_('Login failed.'), 'error')

    return {'form': form}
