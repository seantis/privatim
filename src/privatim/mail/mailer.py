from __future__ import annotations
import base64
import io
import json
import re
from email.headerregistry import Address
from string import ascii_letters
from string import digits

import requests
from zope.interface import implementer

from .exceptions import InactiveRecipient
from .exceptions import MailConnectionError
from .exceptions import MailError
from .interfaces import IMailer
from .types import MailState


from typing import Any
from typing import ClassVar
from typing import cast
from typing import overload
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from requests import Response
    from collections.abc import Sequence
    from ..types import JSON
    from ..types import JSONArray
    from ..types import JSONObject
    from .types import MailAttachment
    from .types import MailParams
    from .types import TemplateMailParams
    MailID = str
    AnyMailParams = MailParams | TemplateMailParams


domain_regex = re.compile(r'@[A-Za-z0-9][A-Za-z0-9.-]*[.][A-Za-z]{2,10}')
plus_regex = re.compile(r'(?<!^)(?<![\s<,])[+][a-zA-Z0-9_.-]+(?=@)')
specials_regex = re.compile(r'[][\\()<>@,:;.]')
alphanumeric = ascii_letters + digits
qp_prefix = '=?utf-8?q?'
qp_suffix = '?='
QP_PREFIX_LENGTH = len(qp_prefix)
QP_SUFFIX_LENGTH = len(qp_suffix)
QP_MAX_WORD_LENGTH = 75
QP_CONTENT_LENGTH = QP_MAX_WORD_LENGTH - QP_PREFIX_LENGTH - QP_SUFFIX_LENGTH


def needs_header_encode(name: str) -> bool:
    # NOTE: Backslash escaping is forbidden in Postmark API
    if '"' in name:
        return True
    try:
        # NOTE: Technically there's some ASCII characters that
        #       should be illegal altogether such as \n, \r, \0
        #       This should already be caught by the use of Address
        #       though, which makes sure each part only contains
        #       legal characters.
        name.encode('ascii')
    except UnicodeEncodeError:
        return True
    return False


def qp_encode_display_name(name: str) -> str:
    words: list[str] = []
    current_word: list[str] = []

    def finish_word() -> None:
        nonlocal current_word
        content = ''.join(current_word)
        words.append(f'{qp_prefix}{content}{qp_suffix}')
        current_word = []

    for character in name:
        if character == ' ':
            # special case for header encoding
            characters = ['_']
        elif character in alphanumeric:
            # no need to encode this character
            characters = [character]
        else:
            # QP encode the character
            characters = list(
                ''.join(f'={c:02X}' for c in character.encode('utf-8'))
            )

        if len(current_word) + len(characters) > QP_CONTENT_LENGTH:
            finish_word()

        current_word.extend(characters)

    finish_word()
    if len(words) == 1:
        # We can omit the enclosing double quotes
        return words[0]

    # NOTE: The enclosing double quotes are necessary so that spaces
    #       as word separators can be parsed correctly.
    return f'"{" ".join(words)}"'


def format_single_address(address: Address) -> str:
    # NOTE: Format the address according to Postmark API rules:
    #       Quoted printable encoded words can be at most 75
    #       characters and we're not allowed to use backslash
    #       escaping for double quotes.
    name = address.display_name
    if not name:
        return address.addr_spec

    if not needs_header_encode(name):
        if specials_regex.search(name):
            # simple quoting works here, since we disallow
            # backslash escaping double quotes.
            name = f'"{name}"'
        return f'{name} <{address.addr_spec}>'

    name = qp_encode_display_name(name)
    return f'{name} <{address.addr_spec}>'


def format_address(addresses: 'Address | Sequence[Address]') -> str:
    if isinstance(addresses, Address):
        addresses = [addresses]
    return ', '.join(format_single_address(a) for a in addresses)


@implementer(IMailer)
class PostmarkMailer:
    api_url:        ClassVar[str] = 'https://api.postmarkapp.com'
    default_sender: str
    server_token:   str
    stream:         str
    blackhole:      bool

    def __init__(self,
                 default_sender: Address,
                 server_token:   str,
                 stream:         str,
                 blackhole:      bool = False) -> None:

        self.default_sender = format_single_address(default_sender)
        self.server_token = server_token
        self.stream = stream
        self.blackhole = blackhole

    def request_headers(self) -> dict[str, str]:
        return {'X-Postmark-Server-Token': self.server_token}

    def prepare_message(self, params: 'AnyMailParams') -> 'JSONObject':
        receivers = format_address(params['receivers'])
        # Strip plus addressing, so it can be used regardless of provider
        # support to disambiguate multiple participants with the same
        # e-mail address.
        # TODO: We could maybe do this in format_single_address?
        receivers = plus_regex.sub('', receivers)
        if self.blackhole:
            receivers = domain_regex.sub(
                '@blackhole.postmarkapp.com', receivers
            )

        message: JSONObject = {
            'From': self.default_sender,
            'To': receivers,
            'MessageStream': self.stream,
            'TrackOpens': True
        }
        if 'sender' in params:
            message['ReplyTo'] = format_single_address(params['sender'])
        if 'content' in params:
            params = cast('MailParams', params)
            message['TextBody'] = params['content']
            message['Subject'] = params['subject']
        elif 'template' in params:
            # NOTE: I'm not sure i like this, but it's better than having
            #       to pass mailer.stream around so much, which shouldn't
            #       necessarily be a standard attribute of IMailer...
            message['TemplateAlias'] = f"{self.stream}-{params['template']}"
            message['TemplateModel'] = params['data']

            if 'subject' in params:
                message['Subject'] = params['subject']

        if 'tag' in params:
            message['Tag'] = params['tag']

        if 'attachments' in params:
            message['Attachments'] = self.prepare_attachments(
                params['attachments']
            )
        return message

    def prepare_attachments(self, attachments: list['MailAttachment']
                            ) -> 'JSONArray':
        result: JSONArray = []
        for attachment in attachments:
            content = base64.b64encode(attachment['content'])
            payload: JSONObject = {
                'Name': attachment['filename'],
                'Content': content.decode('ascii'),
                'ContentType': attachment['content_type'],
            }
            if 'content_id' in attachment:
                payload['ContentID'] = 'cid:' + attachment['content_id']
            result.append(payload)
        return result

    def get_response_data(self, response: 'Response') -> 'JSON':
        try:
            data = response.json()
            if not response.ok:
                raise MailError(data['Message'])
            return data
        except (ValueError, KeyError) as exception:
            raise MailError(
                'Malformed response from Postmark API'
            ) from exception

    def _raw_send(self, api_path: str, params: 'AnyMailParams') -> 'MailID':
        send_url = self.api_url + api_path
        send_data = self.prepare_message(params)
        headers = self.request_headers()
        try:
            response = requests.post(
                send_url,
                json=send_data,
                headers=headers,
                timeout=(5, 10)
            )
        except ConnectionError as exception:
            raise MailConnectionError(
                'Failed to connect to Postmark API') from exception
        data = self.get_response_data(response)
        if not isinstance(data, dict):
            raise MailError('Invalid API data.')

        if data['ErrorCode'] == 406:
            raise InactiveRecipient()
        elif data['ErrorCode'] != 0:
            raise MailError(data['Message'])
        return data['MessageID']  # type:ignore[return-value]

    def send(self,
             sender:      Address | None,
             receivers:   'Address | Sequence[Address]',
             subject:     str,
             content:     str,
             *,
             tag:         str | None = None,
             attachments: list['MailAttachment'] | None = None,
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

        return self._raw_send('/email', params)

    def send_template(self,
                      sender:      Address | None,
                      receivers:   'Address | Sequence[Address]',
                      template:    str,
                      data:        'JSONObject',
                      *,
                      subject:     str | None = None,
                      tag:         str | None = None,
                      attachments: list['MailAttachment'] | None = None,
                      **kwargs:    Any) -> 'MailID':

        params: TemplateMailParams = {
            'receivers': receivers,
            'template': template,
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

        return self._raw_send('/email/withTemplate', params)

    # NOTE: For now we disallow mixing MailParams for the purpose of
    #       preventing users from specifying a template for MailParams.
    #       Technically this should not cause any problem however, so
    #       we could allow it in the future if we really needed it.
    @overload
    def _raw_bulk_send(self,
                       api_path: str,
                       mails:    'Sequence[MailParams]',
                       *,
                       preamble: bytes = b'{"messages":[',
                       postamble: bytes = b']}'
                       ) -> list['MailID' | MailState]: ...

    @overload
    def _raw_bulk_send(self,
                       api_path: str,
                       mails:    'Sequence[TemplateMailParams]',
                       template: str | None = None,
                       *,
                       preamble: bytes = b'{"messages":[',
                       postamble: bytes = b']}'
                       ) -> list['MailID' | MailState]: ...

    def _raw_bulk_send(self,
                       api_path: str,
                       mails:    'Sequence[AnyMailParams]',
                       template: str | None = None,
                       *,
                       # NOTE: annoyingly Postmark either has a wrapper
                       #       around the array or not depending on the
                       #       api call so we need to handle this using
                       #       these arguments
                       preamble: bytes = b'{"Messages": [',
                       postamble: bytes = b']}'
                       ) -> list['MailID' | MailState]:

        messages: JSONArray = []
        for mail in mails:
            if template:
                mail = cast('TemplateMailParams', mail)
                # NOTE: This modifies the original dict, which could
                #       be a source for errors, but it's also faster...
                mail.setdefault('template', template)
            messages.append(self.prepare_message(mail))

        bulk_url = self.api_url + api_path
        headers = self.request_headers()
        # We generate the payload ourselves so we set the headers manually
        headers['Accept'] = 'application/json'
        headers['Content-Type'] = 'application/json'
        BATCH_LIMIT = 500
        # NOTE: The API specifies MB, so let's not chance it
        #       by assuming they meant MiB and just go with
        #       lower size limit.
        SIZE_LIMIT = 50_000_000  # 50MB
        # NOTE: We use a buffer to be a bit more memory efficient
        #       we don't initialize the buffer, so tell gives us
        #       the exact size of the buffer.
        buffer = io.BytesIO()
        buffer.write(preamble)
        num_included = 0
        result: list[MailID | MailState] = []

        def finish_batch() -> None:
            nonlocal buffer
            nonlocal num_included

            buffer.write(postamble)

            # if the batch is empty we just skip it
            if num_included > 0:
                assert num_included <= BATCH_LIMIT
                assert buffer.tell() <= SIZE_LIMIT

                try:
                    response = requests.post(
                        bulk_url,
                        data=buffer.getvalue(),
                        headers=headers,
                        timeout=(5, 10)
                    )
                    data = self.get_response_data(response)
                    if not isinstance(data, list) or len(data) != num_included:
                        # TODO: should probably log this as a warning
                        raise MailError('Invalid API data.')

                    for message in data:
                        if (
                            not isinstance(message, dict)
                            or 'ErrorCode' not in message
                            or 'MessageID' not in message
                        ):
                            # TODO: should probably log this as a warning
                            result.append(MailState.failed)
                            continue

                        error_code = message['ErrorCode']
                        if error_code == 406:
                            result.append(MailState.inactive_recipient)
                        elif error_code != 0:
                            result.append(MailState.failed)
                        else:
                            # if we don't get an ID we don't want to fail hard
                            # so we just pretend the mail has been delivered
                            result.append(message['MessageID'])  # type:ignore

                except ConnectionError:
                    # we'll treat these as a temporary failures
                    result.extend([MailState.temporary_failure]*num_included)
                except MailError:
                    # we'll treat these as more permanent failures for now
                    result.extend([MailState.failed]*num_included)

            # prepare vars for next batch
            buffer.close()
            buffer = io.BytesIO()
            buffer.write(preamble)
            num_included = 0

        for message in messages:
            payload = json.dumps(message).encode('utf-8')
            if buffer.tell() + len(payload) + len(postamble) >= SIZE_LIMIT:
                finish_batch()

            if num_included:
                buffer.write(b',')

            buffer.write(payload)
            num_included += 1

            if num_included == BATCH_LIMIT:
                finish_batch()

        # finish final partially full batch
        finish_batch()
        return result

    def bulk_send(self, mails: list['MailParams']
                  ) -> list['MailID' | MailState]:
        return self._raw_bulk_send('/email/batch', mails,
                                   preamble=b'[', postamble=b']')

    def bulk_send_template(self,
                           mails: list['TemplateMailParams'],
                           default_template: str | None = None,
                           ) -> list['MailID' | MailState]:
        return self._raw_bulk_send(
            '/email/batchWithTemplates', mails, default_template
        )

    def get_message_details(self, message_id: 'MailID') -> 'JSON':
        details_url = f'{self.api_url}/messages/outbound/{message_id}/details'
        headers = self.request_headers()
        headers['Accept'] = 'application/json'
        try:
            response = requests.get(
                details_url,
                headers=headers,
                timeout=(5, 10)
            )
        except ConnectionError as exception:
            raise MailConnectionError(
                'Failed to connect to Postmark API') from exception
        return self.get_response_data(response)

    def get_message_state(self, message_id: 'MailID') -> MailState:
        # NOTE: With multiple recipients for a single mail Postmark will report
        #       a status for each recipient individually. So if we ever specify
        #       multiple recipients, this method will be wrong.
        details = self.get_message_details(message_id)
        if (
            not isinstance(details, dict)
            or not isinstance(details['MessageEvents'], list)
        ):
            raise MailError('Invalid API data.')

        state = max(
            (
                message_event_type_to_mail_state.get(event_type, -1)
                for event in details['MessageEvents']
                if isinstance(event, dict)
                if isinstance((event_type := event['Type']), str)
            ),
            default=-1
        )
        if state < 0:
            return MailState.submitted
        elif state == 0:
            return MailState.bounced
        return cast('MailState', state)

    def validate_template(self, template_data: dict[str, str]) -> list[str]:
        validate_url = self.api_url + '/templates/validate'
        try:
            response = requests.post(
                validate_url,
                json=template_data,
                headers=self.request_headers(),
                timeout=(5, 10)
            )
            if not response.ok:
                return ['Template failed to validate.']

            data = response.json()
            if data['AllContentIsValid']:
                return []
            return (
                data['Subject']['ValidationErrors'] +
                data['HtmlBody']['ValidationErrors'] +
                data['TextBody']['ValidationErrors']
            )
        except ConnectionError as exception:
            raise MailConnectionError(
                'Failed to connect to Postmark API') from exception

    def template_exists(self, alias: str) -> bool:
        template_url = self.api_url + '/templates/' + alias
        try:
            headers = self.request_headers()
            headers['Accept'] = 'application/json'
            response = requests.get(
                template_url,
                headers=headers,
                timeout=(5, 10)
            )
            return response.ok
        except ConnectionError as exception:
            raise MailConnectionError(
                'Failed to connect to Postmark API') from exception


message_event_type_to_mail_state = {
    'Delivered': MailState.delivered,
    'Transient': 0,  # Needs to have lower priority than hard bounce
    'Bounced': MailState.failed,  # This is a hard bounce
    'Opened': MailState.read,
}
