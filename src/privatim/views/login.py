
from typing import TYPE_CHECKING

from pyramid.httpexceptions import HTTPFound
from pyramid.security import remember
from sedate import utcnow
from wtforms import Form
from wtforms import PasswordField
from wtforms import StringField
from wtforms import validators

from privatim.models import User

if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim import RenderDataOrRedirect


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
        query = session.query(User)
        query = query.filter(User.email.ilike(login))
        user = query.first()
        if user and user.check_password(password):
            next_url = request.route_url('home')
            user.last_login = utcnow()
            headers = remember(request, user.id)
            from sqlalchemy.orm import object_session  # nocheckin
            assert object_session(user)
            return HTTPFound(location=next_url, headers=headers)

        request.messages.add('Login failed.', 'error')

    return {'form': form}
