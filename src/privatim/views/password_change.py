import logging
from typing import TYPE_CHECKING

from pyramid.httpexceptions import HTTPFound
from wtforms import Form
from wtforms import PasswordField
from wtforms import StringField
from wtforms.validators import InputRequired

from privatim.i18n import _

from ..models import PasswordChangeToken
from ..security_policy import PasswordException
from ..wtform.validators import password_validator

if TYPE_CHECKING:
    from pyramid.interfaces import IRequest

    from ..types import RenderDataOrRedirect

logger = logging.getLogger('privatim.auth')


class PasswordChangeForm(Form):

    email = StringField(
        label=_('Email'),
        validators=[
            InputRequired(),
        ]
    )
    password = PasswordField(
        label=_('New Password'),
        validators=[
            InputRequired(),
            password_validator
        ]
    )
    password_confirmation = PasswordField(
        label=_('Confirm New Password'),
        validators=[
            InputRequired()
        ]
    )


def get_token(
    token:   str,
    request: 'IRequest'
) -> PasswordChangeToken | None:

    session = request.dbsession
    query = session.query(PasswordChangeToken)
    query = query.filter(PasswordChangeToken.token == token)
    return query.first()


def password_change_view(request: 'IRequest') -> 'RenderDataOrRedirect':

    form = PasswordChangeForm(formdata=request.POST)
    if 'email' in request.POST:
        if form.validate():
            token = request.GET.get('token', '')
            email = form.email.data.lower()
            password = form.password.data
            try:
                token_obj = get_token(token, request)
                if not token_obj:
                    raise PasswordException(f'Token "{token}" not found')
                token_obj.consume(email)
                token_obj.user.set_password(password)
                request.messages.add(_('Password changed'), 'success')
                return HTTPFound(request.route_url('login'))
            except PasswordException as e:
                msg = f'Password change: {str(e)}'
                logger.warning(msg)
                request.messages.add('Invalid Request', 'error')
        else:
            msg = _(
                'There was a problem with your submission. Errors have '
                'been highlighted below.'
            )
            request.messages.add(msg, 'error')

    else:
        msg = _(
            'Password must have minimal length of 8 characters, contain one '
            'upper case letter, one lower case letter, one digit and one '
            'special character.'
        )
        request.messages.add(msg, 'info')

    token = request.GET.get('token', '')
    token_obj = get_token(token, request)
    valid = True
    if token_obj and (token_obj.expired or token_obj.consumed):
        valid = False
        msg = 'This password reset link has expired.'
        request.messages.clear()
        request.messages.add(msg, 'error')

    return {
        'form': form,
        'valid': valid,
    }
