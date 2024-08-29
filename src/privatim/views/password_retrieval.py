import logging
from email.headerregistry import Address
from typing import TYPE_CHECKING

from pyramid.httpexceptions import HTTPFound
from wtforms import StringField
from wtforms.validators import InputRequired

from privatim.i18n import _
from privatim.forms.core import Form as BaseForm

from ..mail import IMailer
from ..models import PasswordChangeToken
from ..models import User
from ..security_policy import PasswordException
from privatim.forms.validators import email_validator

if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from sqlalchemy.orm import Session

    from ..types import RenderDataOrRedirect

logger = logging.getLogger('privatim.auth')


class PasswordRetrievalForm(BaseForm):
    email = StringField(
        label='Email',
        validators=[
            InputRequired(),
            email_validator
        ]
    )


def expire_all_tokens(user: User, session: 'Session') -> None:
    query = session.query(PasswordChangeToken)
    query = query.filter(PasswordChangeToken.user_id == user.id)
    query = query.filter(
        PasswordChangeToken.time_expired.is_(None)
    )
    for token in query:
        token.expire()


def mail_retrieval(email: str, request: 'IRequest') -> None:
    # NOTE: This will probably get caught by email_validator
    #       but lets just be safe for now...
    if '\x00' in email:
        raise PasswordException(f'Invalid email "{email}"')

    session = request.dbsession
    query = session.query(User)
    query = query.filter(User.email.ilike(email))
    user = query.first()
    if not user:
        raise PasswordException(f'User "{email}" not found')

    expire_all_tokens(user, session)
    ip_address = getattr(request, 'client_addr', '')
    token_obj = PasswordChangeToken(user, ip_address)
    session.add(token_obj)
    session.flush()

    mailer = request.registry.getUtility(IMailer)
    mailer.send_template(
        sender=None,  # This mail doesn't need a reply-to
        receivers=Address(user.fullname_without_abbrev, addr_spec=user.email),
        template='password-reset',
        data={
            'name': user.fullname_without_abbrev,
            'action_url': request.route_url(
                'password_change',
                _query={'token': token_obj.token}
            )
        },
        tag='password-reset',
    )


def password_retrieval_view(request: 'IRequest') -> 'RenderDataOrRedirect':
    form = PasswordRetrievalForm(formdata=request.POST)
    if 'email' in request.POST and form.validate():
        try:
            assert isinstance(form.email.data, str)
            email = form.email.data.lower()
            mail_retrieval(email, request)
            logger.info(f'Password retrieval mail sent to "{email}"')
        except PasswordException as e:
            logger.warning(
                f'[{request.client_addr}] password retrieval: {str(e)}'
            )

        msg = _(
            'An email has been sent to the requested account with further '
            'information. If you do not receive an email then please '
            'confirm you have entered the correct email address.'
        )
        request.messages.add(msg, 'success')
        return HTTPFound(location=request.route_url('login'))

    return {'form': form}
