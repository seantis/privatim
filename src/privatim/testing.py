import json
from zope.interface import implementer

import pyramid.testing as testing
from webob.acceptparse import accept_language_property
from webob.multidict import MultiDict
from zope.interface.verify import verifyClass

from privatim.flash import MessageQueue
from privatim.i18n import _
from privatim.mail import IMailer
from privatim.mail import MailError
from privatim.security import authenticated_user
from privatim.sms.interfaces import ISMSGateway

from typing import Dict
from typing import List
from typing import NamedTuple
from typing import Optional
from typing import Sequence
from typing import Union
from typing import Any, TYPE_CHECKING
if TYPE_CHECKING:
    from zope.interface.interfaces import IInterface
    from privatim.models import User
    from email.headerregistry import Address

    from .mail import MailState
    from .mail.types import MailAttachment
    from .mail.types import MailParams
    from .mail.types import TemplateMailParams
    from .types import JSON
    from .types import JSONObject
    Mail = Union[MailParams, TemplateMailParams]
    MailID = int


class DummyRequest(testing.DummyRequest):

    accept_language = accept_language_property()

    def __init__(
        self,
        params:   MultiDict[str, str] | None = None,
        environ:  dict[str, Any] | None = None,
        headers:  dict[str, str] | None = None,
        path:     str = '/',
        cookies:  dict[str, str] | None = None,
        post:     MultiDict[str, str] | None = None,
        **kwargs: Any
    ):

        params = params if params else MultiDict()
        kwargs.setdefault('is_xhr', False)
        kwargs.setdefault('client_addr', '127.0.0.1')

        testing.DummyRequest.__init__(
            self, params, environ, headers, path, cookies, post, **kwargs
        )
        self.messages = MessageQueue(self)
        self.exception = None

    @property
    def user(self) -> 'User | None':
        return authenticated_user(self)


def verify_interface(klass: type[Any], interface: 'IInterface') -> None:
    assert interface.implementedBy(klass)
    assert verifyClass(interface, klass)


# translation strings used for testing
_('Just a test')
_('<b>bold</b>', markup=True)


@implementer(IMailer)
class DummyMailer:
    stream:           str = 'dummy'
    mails:            List['Mail']
    sent:             int
    error_state:      Optional['MailState']
    raise_mail_error: bool

    def __init__(self) -> None:
        self.mails = []
        self.sent = 0
        self.error_state = None
        self.raise_mail_error = False

    def flush(self) -> None:
        self.mails = []
        self.sent = 0

    def maybe_raise(self, batch_mode: bool = False) -> None:
        if (
                self.raise_mail_error or
                (self.error_state is not None and not batch_mode)
        ):
            raise MailError('Failed sending mail.')

    def queue(self, mail: 'Mail') -> 'MailID':
        self.maybe_raise()
        self.mails.append(mail)
        self.sent += 1
        return self.sent - 1

    def batch_queue(self, mail: 'Mail') -> Union['MailID', 'MailState']:
        self.maybe_raise(batch_mode=True)
        if self.error_state is not None:
            return self.error_state
        self.mails.append(mail)
        self.sent += 1
        return self.sent - 1

    def send(self,
             sender:      Optional['Address'],
             receivers:   Union['Address', Sequence['Address']],
             subject:     str,
             content:     str,
             *,
             tag:         Optional[str] = None,
             attachments: Optional[List['MailAttachment']] = None,
             **kwargs:    Any) -> 'MailID':
        params: MailParams = {
            'receivers': receivers,
            'subject': subject,
            'content': content
        }
        if sender:
            params['sender'] = sender
        if tag:
            params['tag'] = tag
        if attachments:
            params['attachments'] = attachments
        return self.queue(params)

    def bulk_send(self,
                  mails: List['MailParams']
                  ) -> List[Union['MailID', 'MailState']]:
        return [self.batch_queue(mail) for mail in mails]

    def send_template(self,
                      sender:      Optional['Address'],
                      receivers:   Union['Address', Sequence['Address']],
                      template:    str,
                      data:        'JSONObject',
                      *,
                      subject:     Optional[str] = None,
                      tag:         Optional[str] = None,
                      attachments: Optional[List['MailAttachment']] = None,
                      **kwargs:    Any) -> 'MailID':

        params: TemplateMailParams = {
            'receivers': receivers,
            # NOTE: Not ideal to have this implementation detail in the
            #       dummy mailer. Maybe there's a better way...
            'template': f'{self.stream}-{template}',
            'data': data
        }
        if sender:
            params['sender'] = sender
        if subject:
            params['subject'] = subject
        if tag:
            params['tag'] = tag
        if attachments:
            params['attachments'] = attachments
        return self.queue(params)

    def bulk_send_template(self,
                           mails: List['TemplateMailParams'],
                           default_template: Optional[str] = None,
                           ) -> List[Union['MailID', 'MailState']]:
        sent = []
        for _mail in mails:
            mail = _mail.copy()
            template = mail.get('template', default_template)
            # NOTE: Not ideal to have this implementation detail in the
            #       dummy mailer. Maybe there's a better way...
            mail['template'] = f'{self.stream}-{template}'

            sent.append(self.batch_queue(mail))
        return sent

    def validate_template(self, template_data: Dict[str, str]) -> List[str]:
        raise NotImplementedError()

    def template_exists(self, alias: str) -> bool:
        raise NotImplementedError()


class Message(NamedTuple):
    receiver: str
    content: str
    sender: str


@implementer(ISMSGateway)
class DummySMSGateway:

    messages: list[Message]

    def __init__(self) -> None:
        self.messages = []

    def send(
            self,
            receivers: 'Sequence[str]',
            content: str,
            sender: str = 'Privatim'
    ) -> None:
        for receiver in receivers:
            self.messages.append(Message(receiver, content, sender))


class MockResponse:
    status_code:  int
    ok:           bool
    json_data:    'JSON'
    text:         str
    content:      bytes
    invalid_json: bool

    def __init__(self,
                 json_data:    Optional['JSON'] = None,
                 invalid_json: bool = False) -> None:
        self.status_code = 200
        self.ok = True
        if not json_data:
            json_data = {}
        self.json_data = json_data
        self.text = json.dumps(json_data)
        self.content = self.text.encode('utf-8')
        self.invalid_json = invalid_json

    def json(self, **kwargs: Any) -> 'JSON':
        if self.invalid_json:
            raise ValueError('Invalid JSON.')
        return self.json_data


class RequestsCall(NamedTuple):
    method: str
    url:    str
    kwargs: Dict[str, Any]


class MockRequests:
    _calls:                List[RequestsCall]
    # default response if no responses have been added
    _response:             MockResponse
    # FIFO single-use responses
    _responses:            List[MockResponse]
    mock_connection_error: bool

    def __init__(self) -> None:
        self._calls = []
        self._response = MockResponse()
        self._responses = []
        self.mock_connection_error = False

    def set_response(self, response: MockResponse) -> None:
        self._response = response

    def add_response(self, response: MockResponse) -> None:
        self._responses.append(response)

    def pop(self) -> List[RequestsCall]:
        calls = self._calls
        self.clear()
        return calls

    def clear(self) -> None:
        self._calls = []

    def mock_method(self,
                    method:   str,
                    url:      str,
                    **kwargs: Any
                    ) -> MockResponse:

        if self.mock_connection_error:
            raise ConnectionError()

        self._calls.append(RequestsCall(method.lower(), url, kwargs))
        return self._responses.pop(0) if self._responses else self._response
