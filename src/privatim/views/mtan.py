from __future__ import annotations
from phonenumbers import PhoneNumberType
from pyramid.httpexceptions import HTTPFound
from pyramid.security import remember
from sedate import utcnow
from sqlalchemy import select
from wtforms import Form
from wtforms import StringField
from wtforms.validators import InputRequired
from wtforms.validators import ValidationError

from privatim.forms.fields import PhoneNumberField
from privatim.i18n import _
from privatim.i18n import translate
from privatim.models import User
from privatim.mtan_tool import MTanException
from privatim.mtan_tool import MTanTool
from privatim.sms.interfaces import ISMSGateway


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from sqlalchemy.orm import Session

    from privatim.types import RenderDataOrRedirect


class MTANForm(Form):
    mtan = StringField(
        _('Token'),
        [InputRequired()],
        render_kw={'autofocus': True}
    )


def mtan_view(request: 'IRequest') -> 'RenderDataOrRedirect':

    user_id = request.session.get('mtan_user', None)
    if user_id is None:
        url = request.route_url('login')
        return HTTPFound(url)

    form = MTANForm(formdata=request.POST if request.POST else None)
    if 'mtan' in request.POST and form.validate():
        assert form.mtan.data is not None
        mtan = form.mtan.data.upper()
        tool = MTanTool(request.dbsession)
        try:
            user = tool.verify(user_id, mtan)
            del request.session['mtan_user']
            tool.expire(user_id, mtan)

            assert user is not None
            user.last_login = utcnow()
            headers = remember(request, user_id)
            mtan_obj = tool.tan(user_id, tool.hash(mtan))
            assert mtan_obj is not None
            return HTTPFound(request.route_url('home'), headers=headers)
        except MTanException:
            # FIXME: log failure for fail2ban
            pass

        request.messages.add(_('Authentication failed'), 'error')

    else:
        request.messages.clear()

    return {'form': form}


class UniqueMobileNumber:

    def __init__(self, session: 'Session', existing_user_id: str) -> None:
        self.session = session
        self.existing_user_id = existing_user_id

    def __call__(self, form: Form, field: PhoneNumberField) -> None:
        stmt = select(
            select(User.id)
            .filter(User.mobile_number == field.data)
            .filter(User.id != self.existing_user_id)
            .exists()
        )
        if self.session.scalar(stmt):
            raise ValidationError(_('Existing mobile number'))


def mtan_setup_view(request: 'IRequest') -> 'RenderDataOrRedirect':

    user_id = request.session.get('mtan_setup_user', None)
    if user_id is None:
        url = request.route_url('login')
        return HTTPFound(url)

    retry_url: str | None = None
    form: Form

    remembered = request.session.get('mtan_mobile_number', None)
    if request.GET.get('different_number', ''):
        mobile_number = None
        if 'mtan_mobile_number' in request.session:
            del request.session['mtan_mobile_number']
    else:
        mobile_number = remembered

    if not mobile_number:
        session = request.dbsession
        user = session.get(User, user_id)
        assert user is not None

        # Mobile number input step
        class MTANSetupForm(Form):
            mobile_number = PhoneNumberField(
                _('Mobile Number'),
                [
                    InputRequired(),
                    UniqueMobileNumber(session, user_id),
                ],
                number_type=PhoneNumberType.MOBILE,
                render_kw={'autofocus': True}
            )

        form = mtan_setup_form = MTANSetupForm(
            formdata=request.POST if request.POST else None,
            mobile_number=remembered
        )

        if 'mobile_number' in request.POST and form.validate():
            mobile_number = mtan_setup_form.mobile_number.data
            assert mobile_number is not None
            request.session['mtan_mobile_number'] = mobile_number

            # Send MTAN
            mtan_tool = MTanTool(session)
            tan = mtan_tool.create_tan(
                user, request.client_addr or '0.0.0.0'  # nosec
            )

            content = _(
                'Privatim Login Token:\n${tan}',
                mapping={'tan': tan}
            )
            locale = request.locale_name
            gateway = request.registry.getUtility(ISMSGateway)
            gateway.send(
                receivers=[mobile_number],
                content=translate(content, locale),
                sender='Privatim'
            )

    if mobile_number:
        form = mtan_form = MTANForm(
            formdata=request.POST if request.POST else None
        )
        retry_url = request.route_url(
            'mtan_setup',
            _query={'different_number': '1'}
        )

        if 'mtan' in request.POST and form.validate():
            assert mtan_form.mtan.data is not None
            mtan = mtan_form.mtan.data.upper()
            tool = MTanTool(request.dbsession)
            try:
                user = tool.verify(user_id, mtan)
                assert user is not None

                # Store mobile number
                user.mobile_number = mobile_number

                del request.session['mtan_setup_user']
                del request.session['mtan_mobile_number']
                tool.expire(user_id, mtan)

                user.last_login = utcnow()
                headers = remember(request, user_id)
                mtan_obj = tool.tan(user_id, tool.hash(mtan))
                assert mtan_obj is not None
                return HTTPFound(request.route_url('home'), headers=headers)
            except MTanException:
                # FIXME: log failure for fail2ban
                pass

            request.messages.add(_('Verification failed'), 'error')

    return {
        'form': form,
        'submit_url': request.path_url,
        'retry_url': retry_url,
    }
