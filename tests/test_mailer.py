import base64
import json
from email.headerregistry import Address
from email.policy import SMTP

import pytest

from privatim.mail import IMailer
from privatim.mail import InactiveRecipient
from privatim.mail import MailConnectionError
from privatim.mail import MailError
from privatim.mail import MailState
from privatim.mail import PostmarkMailer
from privatim.mail.mailer import format_single_address
from privatim.mail.mailer import needs_header_encode
from privatim.mail.mailer import plus_regex
from privatim.testing import MockResponse
from privatim.testing import verify_interface


def addr(email, name=''):
    # let's keep the code a bit shorter...
    return Address(name, addr_spec=email)


def test_needs_header_encode():
    assert needs_header_encode('test') is False
    assert needs_header_encode('"') is True
    assert needs_header_encode('ö') is True


def test_format_single_address():
    # basic case
    assert format_single_address(
        addr('test@example.com')
    ) == 'test@example.com'
    # basic case with a display name
    assert format_single_address(
        addr('test@example.com', 'Test')
    ) == 'Test <test@example.com>'
    # display name with special character
    assert format_single_address(
        addr('test@example.com', 'Test.')
    ) == '"Test." <test@example.com>'
    # display name with double quote
    assert format_single_address(
        addr('test@example.com', 'Test"')
    ) == '=?utf-8?q?Test=22?= <test@example.com>'
    # display name with non-ascii character
    assert format_single_address(
        addr('test@example.com', 'Test ä')
    ) == '=?utf-8?q?Test_=C3=A4?= <test@example.com>'
    # too long qp encoded display name
    name = 'Test "' + 'a'*160
    formatted = format_single_address(
        addr('test@example.com', name)
    )
    assert formatted == (
        '"=?utf-8?q?Test_=22' + 'a'*55 +
        '?= =?utf-8?q?' + 'a'*63 +
        '?= =?utf-8?q?' + 'a'*42 +
        '?=" <test@example.com>'
    )
    # make sure we can still parse this as a header
    header = SMTP.header_factory('sender', formatted)
    # and we end up back with what we put in originally
    assert header.address.display_name == name

    # extract only the encoded words from the formatted address
    words = formatted[1:-len('" <test@example.com>')].split(' ')
    # make sure each word is at most 75 characters
    assert all(len(part) <= 75 for part in words)


def test_interface():
    verify_interface(PostmarkMailer, IMailer)


def test_request_headers():
    mailer = PostmarkMailer(
        addr('nr@example.com'),
        'secret-token',
        'development'
    )
    assert mailer.request_headers() == {
        'X-Postmark-Server-Token': 'secret-token'
    }


def test_send(mock_requests):
    response = MockResponse({'MessageID': 100, 'ErrorCode': 0})
    mock_requests.set_response(response)

    mailer = PostmarkMailer(
        addr('nr@example.com'),
        'secret-token',
        'development'
    )
    assert mailer.send(
        addr('sender@example.com'),
        [addr('recipient1@example.com'), addr('recipient2@example.com')],
        'Test Subject',
        'Test Content'
    ) == 100

    requests = mock_requests.pop()
    assert len(requests) == 1
    assert requests[0].method == 'post'
    assert requests[0].url == 'https://api.postmarkapp.com/email'
    kwargs = requests[0].kwargs
    assert kwargs['headers'] == {
        'X-Postmark-Server-Token': 'secret-token'
    }
    assert kwargs['json'] == {
        'From': 'nr@example.com',
        'To': 'recipient1@example.com, recipient2@example.com',
        'ReplyTo': 'sender@example.com',
        'MessageStream': 'development',
        'TrackOpens': True,
        'TextBody': 'Test Content',
        'Subject': 'Test Subject',
    }


def test_send_blackhole(mock_requests):
    response = MockResponse({'MessageID': 100, 'ErrorCode': 0})
    mock_requests.set_response(response)

    mailer = PostmarkMailer(
        addr('nr@example.com'),
        'secret-token',
        'development',
        blackhole=True
    )
    assert mailer.send(
        addr('sender@example.com'),
        [
            addr('recipient1@example.com'),
            addr('recipient2@example.com', 'Named Recipient'),
        ],
        'Test Subject',
        'Test Content'
    ) == 100

    requests = mock_requests.pop()
    assert len(requests) == 1
    assert requests[0].method == 'post'
    assert requests[0].url == 'https://api.postmarkapp.com/email'
    kwargs = requests[0].kwargs
    assert kwargs['headers'] == {
        'X-Postmark-Server-Token': 'secret-token'
    }
    assert kwargs['json'] == {
        'From': 'nr@example.com',
        'To': (
            'recipient1@blackhole.postmarkapp.com, '
            'Named Recipient <recipient2@blackhole.postmarkapp.com>'
        ),
        'ReplyTo': 'sender@example.com',
        'MessageStream': 'development',
        'TrackOpens': True,
        'TextBody': 'Test Content',
        'Subject': 'Test Subject',
    }


def test_plus_regex():
    assert plus_regex.sub(
        '', 'shared+recipient1@example.com'
    ) == 'shared@example.com'
    assert plus_regex.sub(
        '', 'Recipient <shared+recipient1@example.com>'
    ) == 'Recipient <shared@example.com>'
    assert plus_regex.sub(
        '', 'shared+recipient1@example.com, shared+recipient2@example.com'
    ) == 'shared@example.com, shared@example.com'
    assert plus_regex.sub(
        '', 'shared+recipient1@example.com,shared+recipient2@example.com'
    ) == 'shared@example.com,shared@example.com'

    # avoid empty addresses
    assert plus_regex.sub(
        '', '+recipient1@example.com'
    ) == '+recipient1@example.com'
    assert plus_regex.sub(
        '', 'Recipient <+recipient1@example.com>'
    ) == 'Recipient <+recipient1@example.com>'
    assert plus_regex.sub(
        '', 'shared+recipient1@example.com, +recipient2@example.com'
    ) == 'shared@example.com, +recipient2@example.com'
    assert plus_regex.sub(
        '', 'shared+recipient1@example.com,+recipient2@example.com'
    ) == 'shared@example.com,+recipient2@example.com'


def test_send_plus_addressing(mock_requests):
    response = MockResponse({'MessageID': 100, 'ErrorCode': 0})
    mock_requests.set_response(response)

    mailer = PostmarkMailer(
        addr('nr@example.com'),
        'secret-token',
        'development'
    )
    assert mailer.send(
        addr('sender@example.com'),
        [
            addr('shared+recipient1@example.com', 'Recipient 1'),
            addr('shared+recipient2@example.com', 'Recipient 2'),
        ],
        'Test Subject',
        'Test Content'
    ) == 100

    requests = mock_requests.pop()
    assert len(requests) == 1
    assert requests[0].method == 'post'
    assert requests[0].url == 'https://api.postmarkapp.com/email'
    kwargs = requests[0].kwargs
    assert kwargs['headers'] == {
        'X-Postmark-Server-Token': 'secret-token'
    }
    assert kwargs['json'] == {
        'From': 'nr@example.com',
        'To': (
            'Recipient 1 <shared@example.com>, '
            'Recipient 2 <shared@example.com>'
        ),
        'ReplyTo': 'sender@example.com',
        'MessageStream': 'development',
        'TrackOpens': True,
        'TextBody': 'Test Content',
        'Subject': 'Test Subject',
    }


def test_send_tagged(mock_requests):
    response = MockResponse({'MessageID': 100, 'ErrorCode': 0})
    mock_requests.set_response(response)

    mailer = PostmarkMailer(
        addr('nr@example.com'),
        'secret-token',
        'development'
    )
    assert mailer.send(
        addr('sender@example.com'),
        [addr('recipient1@example.com'), addr('recipient2@example.com')],
        'Test Subject',
        'Test Content',
        tag='test'
    ) == 100

    requests = mock_requests.pop()
    assert len(requests) == 1
    assert requests[0].method == 'post'
    assert requests[0].url == 'https://api.postmarkapp.com/email'
    kwargs = requests[0].kwargs
    assert kwargs['headers'] == {
        'X-Postmark-Server-Token': 'secret-token'
    }
    assert kwargs['json'] == {
        'From': 'nr@example.com',
        'To': 'recipient1@example.com, recipient2@example.com',
        'ReplyTo': 'sender@example.com',
        'MessageStream': 'development',
        'TrackOpens': True,
        'TextBody': 'Test Content',
        'Subject': 'Test Subject',
        'Tag': 'test',
    }


def test_send_attachments(mock_requests):
    response = MockResponse({'MessageID': 100, 'ErrorCode': 0})
    mock_requests.set_response(response)

    mailer = PostmarkMailer(
        addr('nr@example.com'),
        'secret-token',
        'development'
    )
    txt_content = b'plain text'
    csv_content = b'user_id,hits,misses\n375,1,2\n12,5,2'
    attachments = [
        {
            'content': txt_content,
            'filename': 'plain.txt',
            'content_type': 'text/plain',
        },
        {
            'content': csv_content,
            'filename': 'accuracy.csv',
            'content_type': 'text/csv',
        },
    ]
    assert mailer.send(
        addr('sender@example.com'),
        [addr('recipient1@example.com'), addr('recipient2@example.com')],
        'Test Subject',
        'Test Content',
        attachments=attachments
    ) == 100

    requests = mock_requests.pop()
    assert len(requests) == 1
    assert requests[0].method == 'post'
    assert requests[0].url == 'https://api.postmarkapp.com/email'
    kwargs = requests[0].kwargs
    assert kwargs['headers'] == {
        'X-Postmark-Server-Token': 'secret-token'
    }
    assert kwargs['json'] == {
        'From': 'nr@example.com',
        'To': 'recipient1@example.com, recipient2@example.com',
        'ReplyTo': 'sender@example.com',
        'MessageStream': 'development',
        'TrackOpens': True,
        'TextBody': 'Test Content',
        'Subject': 'Test Subject',
        'Attachments': [
            {
                'Name': 'plain.txt',
                'Content': base64.b64encode(txt_content).decode('ascii'),
                'ContentType': 'text/plain',
            },
            {
                'Name': 'accuracy.csv',
                'Content': base64.b64encode(csv_content).decode('ascii'),
                'ContentType': 'text/csv',
            },
        ],
    }


def test_send_connection_error(mock_requests):
    mock_requests.mock_connection_error = True
    mailer = PostmarkMailer(
        addr('nr@example.com'),
        'secret-token',
        'development'
    )
    with pytest.raises(MailConnectionError):
        mailer.send(
            addr('sender@example.com'),
            [addr('recipient1@example.com'), addr('recipient2@example.com')],
            'Test Subject',
            'Test Content'
        )


def test_send_malformed_response(mock_requests):
    response = MockResponse(invalid_json=True)
    mock_requests.set_response(response)

    mailer = PostmarkMailer(
        addr('nr@example.com'),
        'secret-token',
        'development'
    )
    with pytest.raises(
        MailError, match=r'Malformed response from Postmark API'
    ):
        mailer.send(
            addr('sender@example.com'),
            [addr('recipient1@example.com'), addr('recipient2@example.com')],
            'Test Subject',
            'Test Content'
        )


def test_send_error_response(mock_requests):
    response = MockResponse({'Message': 'This is the error', 'ErrorCode': 100})
    mock_requests.set_response(response)

    mailer = PostmarkMailer(
        addr('nr@example.com'),
        'secret-token',
        'development'
    )
    with pytest.raises(
        MailError, match=r'This is the error'
    ):
        mailer.send(
            addr('sender@example.com'),
            [addr('recipient1@example.com'), addr('recipient2@example.com')],
            'Test Subject',
            'Test Content'
        )

    response.ok = False
    with pytest.raises(
        MailError, match=r'This is the error'
    ):
        mailer.send(
            addr('sender@example.com'),
            [addr('recipient1@example.com'), addr('recipient2@example.com')],
            'Test Subject',
            'Test Content'
        )


def test_send_inactive_recipient(mock_requests):
    response = MockResponse(
        {'Message': 'This is the error', 'ErrorCode': 406}
    )
    mock_requests.set_response(response)

    mailer = PostmarkMailer(
        addr('nr@example.com'),
        'secret-token',
        'development'
    )
    with pytest.raises(InactiveRecipient):
        mailer.send(
            addr('sender@example.com'),
            [addr('recipient1@example.com'), addr('recipient2@example.com')],
            'Test Subject',
            'Test Content'
        )


def test_send_template(mock_requests):
    response = MockResponse({'MessageID': 100, 'ErrorCode': 0})
    mock_requests.set_response(response)

    mailer = PostmarkMailer(
        addr('nr@example.com'),
        'secret-token',
        'development'
    )
    assert mailer.send_template(
        addr('sender@example.com'),
        [addr('recipient1@example.com'), addr('recipient2@example.com')],
        'template',
        {'name': 'John Doe'}
    ) == 100

    requests = mock_requests.pop()
    assert len(requests) == 1
    assert requests[0].method == 'post'
    assert requests[0].url == (
        'https://api.postmarkapp.com/email/withTemplate'
    )
    kwargs = requests[0].kwargs
    assert kwargs['headers'] == {
        'X-Postmark-Server-Token': 'secret-token'
    }
    assert kwargs['json'] == {
        'From': 'nr@example.com',
        'To': 'recipient1@example.com, recipient2@example.com',
        'ReplyTo': 'sender@example.com',
        'MessageStream': 'development',
        'TrackOpens': True,
        'TemplateAlias': 'development-template',
        'TemplateModel': {'name': 'John Doe'},
    }


def test_send_template_with_subject(mock_requests):
    response = MockResponse({'MessageID': 100, 'ErrorCode': 0})
    mock_requests.set_response(response)

    mailer = PostmarkMailer(
        addr('nr@example.com'),
        'secret-token',
        'development'
    )
    assert mailer.send_template(
        addr('sender@example.com'),
        [addr('recipient1@example.com'), addr('recipient2@example.com')],
        'template',
        {'name': 'John Doe'},
        subject='Test Subject'
    ) == 100

    requests = mock_requests.pop()
    assert len(requests) == 1
    assert requests[0].method == 'post'
    assert requests[0].url == (
        'https://api.postmarkapp.com/email/withTemplate'
    )
    kwargs = requests[0].kwargs
    assert kwargs['headers'] == {
        'X-Postmark-Server-Token': 'secret-token'
    }
    assert kwargs['json'] == {
        'From': 'nr@example.com',
        'To': 'recipient1@example.com, recipient2@example.com',
        'ReplyTo': 'sender@example.com',
        'MessageStream': 'development',
        'TrackOpens': True,
        'TemplateAlias': 'development-template',
        'TemplateModel': {'name': 'John Doe'},
        'Subject': 'Test Subject',
    }


def test_bulk_send(mock_requests):
    response = MockResponse(
        [
            {'MessageID': 100, 'ErrorCode': 0},
            {'MessageID': 101, 'ErrorCode': 406},
            {'MessageID': 102, 'ErrorCode': 400},
        ]
    )
    mock_requests.set_response(response)

    mailer = PostmarkMailer(
        addr('nr@example.com'),
        'secret-token',
        'development'
    )
    assert mailer.bulk_send([
        {
            'sender': addr('sender1@example.com'),
            'receivers': [addr('recipient1@example.com')],
            'subject': 'Test Subject 1',
            'content': 'Test Content 1'
        },
        {
            'sender': addr('sender2@example.com'),
            'receivers': [addr('recipient2@example.com')],
            'subject': 'Test Subject 2',
            'content': 'Test Content 2'
        },
        {
            'sender': addr('sender3@example.com'),
            'receivers': addr('recipient3@example.com'),
            'subject': 'Test Subject 3',
            'content': 'Test Content 3'
        },
    ]) == [100, MailState.inactive_recipient, MailState.failed]

    requests = mock_requests.pop()
    assert len(requests) == 1
    assert requests[0].method == 'post'
    assert requests[0].url == 'https://api.postmarkapp.com/email/batch'
    kwargs = requests[0].kwargs
    assert kwargs['headers'] == {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-Postmark-Server-Token': 'secret-token'
    }
    assert json.loads(kwargs['data'].decode('utf-8')) == [
        {
            'From': 'nr@example.com',
            'To': 'recipient1@example.com',
            'ReplyTo': 'sender1@example.com',
            'MessageStream': 'development',
            'TrackOpens': True,
            'TextBody': 'Test Content 1',
            'Subject': 'Test Subject 1',
        },
        {
            'From': 'nr@example.com',
            'To': 'recipient2@example.com',
            'ReplyTo': 'sender2@example.com',
            'MessageStream': 'development',
            'TrackOpens': True,
            'TextBody': 'Test Content 2',
            'Subject': 'Test Subject 2',
        },
        {
            'From': 'nr@example.com',
            'To': 'recipient3@example.com',
            'ReplyTo': 'sender3@example.com',
            'MessageStream': 'development',
            'TrackOpens': True,
            'TextBody': 'Test Content 3',
            'Subject': 'Test Subject 3',
        },
    ]


def test_bulk_send_batched(mock_requests):
    mock_requests.add_response(MockResponse(
        [
            {'MessageID': index, 'ErrorCode': 0}
            for index in range(100, 600)
        ]
    ))
    mock_requests.add_response(MockResponse(
        [
            {'MessageID': index, 'ErrorCode': 0}
            for index in range(600, 1100)
        ]
    ))
    mock_requests.add_response(MockResponse(
        [
            {'MessageID': index, 'ErrorCode': 0}
            for index in range(1100, 1150)
        ]
    ))

    mailer = PostmarkMailer(
        addr('nr@example.com'),
        'secret-token',
        'development'
    )
    assert mailer.bulk_send([
        {
            'sender': addr('sender1@example.com'),
            'receivers': [addr('recipient1@example.com')],
            'subject': f'Test Subject {index}',
            'content': f'Test Content {index}'
        }
        for index in range(1050)
    ]) == list(range(100, 1150))

    requests = mock_requests.pop()
    assert len(requests) == 3
    assert requests[0].method == 'post'
    assert requests[0].url == 'https://api.postmarkapp.com/email/batch'
    kwargs = requests[0].kwargs
    assert kwargs['headers'] == {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-Postmark-Server-Token': 'secret-token'
    }
    assert len(kwargs['data']) <= 50_000_000
    payload = json.loads(kwargs['data'].decode('utf-8'))
    assert len(payload) == 500
    assert requests[1].method == 'post'
    assert requests[1].url == 'https://api.postmarkapp.com/email/batch'
    kwargs = requests[1].kwargs
    assert kwargs['headers'] == {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-Postmark-Server-Token': 'secret-token'
    }
    assert len(kwargs['data']) <= 50_000_000
    payload = json.loads(kwargs['data'].decode('utf-8'))
    assert len(payload) == 500
    assert requests[2].method == 'post'
    assert requests[2].url == 'https://api.postmarkapp.com/email/batch'
    kwargs = requests[2].kwargs
    assert kwargs['headers'] == {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-Postmark-Server-Token': 'secret-token'
    }
    assert len(kwargs['data']) <= 50_000_000
    payload = json.loads(kwargs['data'].decode('utf-8'))
    assert len(payload) == 50


def test_bulk_send_batched_max_size(mock_requests):
    mock_requests.add_response(MockResponse(
        [
            {'MessageID': index, 'ErrorCode': 0}
            for index in range(100, 104)
        ]
    ))
    mock_requests.add_response(MockResponse(
        [
            {'MessageID': index, 'ErrorCode': 0}
            for index in range(104, 108)
        ]
    ))
    mock_requests.add_response(MockResponse(
        [
            {'MessageID': index, 'ErrorCode': 0}
            for index in range(108, 110)
        ]
    ))

    mailer = PostmarkMailer(
        addr('nr@example.com'),
        'secret-token',
        'development'
    )
    assert mailer.bulk_send([
        {
            'sender': addr('sender1@example.com'),
            'receivers': [addr('recipient1@example.com')],
            'subject': f'Test Subject {index}',
            'content': 'a' * 10_000_000  # 10 MB
        }
        for index in range(10)
    ]) == list(range(100, 110))

    requests = mock_requests.pop()
    assert len(requests) == 3
    assert requests[0].method == 'post'
    assert requests[0].url == 'https://api.postmarkapp.com/email/batch'
    kwargs = requests[0].kwargs
    assert kwargs['headers'] == {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-Postmark-Server-Token': 'secret-token'
    }
    assert len(kwargs['data']) <= 50_000_000
    payload = json.loads(kwargs['data'].decode('utf-8'))
    assert len(payload) == 4
    assert requests[1].method == 'post'
    assert requests[1].url == 'https://api.postmarkapp.com/email/batch'
    kwargs = requests[1].kwargs
    assert kwargs['headers'] == {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-Postmark-Server-Token': 'secret-token'
    }
    assert len(kwargs['data']) <= 50_000_000
    payload = json.loads(kwargs['data'].decode('utf-8'))
    assert len(payload) == 4
    assert requests[2].method == 'post'
    assert requests[2].url == 'https://api.postmarkapp.com/email/batch'
    kwargs = requests[2].kwargs
    assert kwargs['headers'] == {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-Postmark-Server-Token': 'secret-token'
    }
    assert len(kwargs['data']) <= 50_000_000
    payload = json.loads(kwargs['data'].decode('utf-8'))
    assert len(payload) == 2


def test_bulk_send_connection_error(mock_requests):
    mock_requests.mock_connection_error = True
    mailer = PostmarkMailer(
        addr('nr@example.com'),
        'secret-token',
        'development'
    )
    assert mailer.bulk_send([{
        'sender': addr('sender1@example.com'),
        'receivers': [addr('recipient1@example.com')],
        'subject': 'Test Subject 1',
        'content': 'Test Content 1'
    }]) == [MailState.temporary_failure]


def test_bulk_send_template(mock_requests):
    response = MockResponse(
        [
            {'MessageID': 100, 'ErrorCode': 0},
            {'MessageID': 101, 'ErrorCode': 406},
            {'MessageID': 102, 'ErrorCode': 400},
        ]
    )
    mock_requests.set_response(response)

    mailer = PostmarkMailer(
        addr('nr@example.com'),
        'secret-token',
        'development'
    )
    assert mailer.bulk_send_template([
        {
            'sender': addr('sender1@example.com'),
            'receivers': [addr('recipient1@example.com')],
            'data': {'name': 'John Doe'}
        },
        {
            'sender': addr('sender2@example.com'),
            'receivers': [addr('recipient2@example.com')],
            'data': {'name': 'Jane Doe'},
            'subject': 'Custom Subject'
        },
        {
            'sender': addr('sender3@example.com'),
            'receivers': addr('recipient3@example.com'),
            'data': {'name': 'Josh Doe'},
            'template': 'other_template'
        },
    ], 'template') == [100, MailState.inactive_recipient, MailState.failed]

    requests = mock_requests.pop()
    assert len(requests) == 1
    assert requests[0].method == 'post'
    assert requests[0].url == (
        'https://api.postmarkapp.com/email/batchWithTemplates'
    )
    kwargs = requests[0].kwargs
    assert kwargs['headers'] == {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-Postmark-Server-Token': 'secret-token'
    }
    assert json.loads(kwargs['data'].decode('utf-8')) == {
        'Messages': [
            {
                'From': 'nr@example.com',
                'To': 'recipient1@example.com',
                'ReplyTo': 'sender1@example.com',
                'MessageStream': 'development',
                'TrackOpens': True,
                'TemplateAlias': 'development-template',
                'TemplateModel': {'name': 'John Doe'},
            },
            {
                'From': 'nr@example.com',
                'To': 'recipient2@example.com',
                'ReplyTo': 'sender2@example.com',
                'MessageStream': 'development',
                'TrackOpens': True,
                'TemplateAlias': 'development-template',
                'TemplateModel': {'name': 'Jane Doe'},
                'Subject': 'Custom Subject',
            },
            {
                'From': 'nr@example.com',
                'To': 'recipient3@example.com',
                'ReplyTo': 'sender3@example.com',
                'MessageStream': 'development',
                'TrackOpens': True,
                'TemplateAlias': 'development-other_template',
                'TemplateModel': {'name': 'Josh Doe'},
            },
        ]
    }


def test_get_message_details(mock_requests):
    response = MockResponse({'Meta': 'Various'})
    mock_requests.set_response(response)

    mailer = PostmarkMailer(
        addr('nr@example.com'),
        'secret-token',
        'development'
    )
    assert mailer.get_message_details('some-message-id') == {
        'Meta': 'Various'
    }

    requests = mock_requests.pop()
    assert len(requests) == 1
    assert requests[0].method == 'get'
    assert requests[0].url == (
        'https://api.postmarkapp.com/messages/outbound/some-message-id/details'
    )
    kwargs = requests[0].kwargs
    assert kwargs['headers'] == {
        'X-Postmark-Server-Token': 'secret-token',
        'Accept': 'application/json'
    }


def test_get_message_details_connection_error(mock_requests):
    mock_requests.mock_connection_error = True
    mailer = PostmarkMailer(
        addr('nr@example.com'),
        'secret-token',
        'development'
    )
    with pytest.raises(MailConnectionError):
        mailer.get_message_details('some-message-id')


def test_get_message_state(mock_requests):
    response = MockResponse({'MessageEvents': []})
    mock_requests.set_response(response)

    mailer = PostmarkMailer(
        addr('nr@example.com'),
        'secret-token',
        'development'
    )
    assert mailer.get_message_state('some-message-id') == MailState.submitted

    response = MockResponse({'MessageEvents': [
        {'Type': 'Transient'}
    ]})
    mock_requests.set_response(response)
    assert mailer.get_message_state('some-message-id') == MailState.bounced

    response = MockResponse({'MessageEvents': [
        {'Type': 'Transient'},
        {'Type': 'Bounced'}
    ]})
    mock_requests.set_response(response)
    assert mailer.get_message_state('some-message-id') == MailState.failed

    response = MockResponse({'MessageEvents': [
        {'Type': 'Transient'},
        {'Type': 'Delivered'}
    ]})
    mock_requests.set_response(response)
    assert mailer.get_message_state('some-message-id') == MailState.delivered

    response = MockResponse({'MessageEvents': [
        {'Type': 'Transient'},
        {'Type': 'Delivered'},
        {'Type': 'Opened'},
    ]})
    mock_requests.set_response(response)
    assert mailer.get_message_state('some-message-id') == MailState.read
