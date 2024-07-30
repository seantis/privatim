from unittest.mock import MagicMock
from unittest.mock import patch
from watchdog.events import FileCreatedEvent

from privatim.sms.tricks import SMSDeliveryTrick


def test_in_smsdir(tmpdir):
    smsdir = tmpdir.mkdir('sms')
    trick = SMSDeliveryTrick(
        smsdir=str(smsdir),
        username='username',
        password='password'
    )

    assert trick.in_smsdir(smsdir.join('message.json'))
    assert not trick.in_smsdir(tmpdir.join('message.json'))


@patch('requests.post')
def test_send_messages_on_init(post, smsdir, gateway):
    SMSDeliveryTrick(
        smsdir=smsdir.path,
        username='username',
        password='password'
    )
    assert len(smsdir.messages()) == 0

    post.return_value = MagicMock(
        json=lambda: {'StatusInfo': 'OK', 'StatusCode': '1'}
    )
    gateway.send(receivers=['+410000000'], content='My message')
    assert len(smsdir.messages()) == 1

    SMSDeliveryTrick(
        smsdir=smsdir.path,
        username='username',
        password='password'
    )
    assert len(smsdir.messages()) == 0
    url = 'https://json.aspsms.com/SendSimpleTextSMS'
    json = {
        'UserName': 'username',
        'Password': 'password',
        'Originator': 'Privatim',
        'Recipients': ['+410000000'],
        'MessageText': 'My message'
    }
    post.assert_called_with(url, json=json)


@patch('requests.post')
def test_on_created(post, smsdir, gateway):
    trick = SMSDeliveryTrick(
        smsdir=smsdir.path,
        username='username',
        password='password'
    )
    assert len(smsdir.messages()) == 0

    post.return_value = MagicMock(
        json=lambda: {'StatusInfo': 'OK', 'StatusCode': '1'}
    )
    gateway.send(receivers=['+410000000'], content='My message')
    assert len(smsdir.messages()) == 1

    event = FileCreatedEvent(smsdir.filenames()[0])
    trick.on_created(event)
    assert len(smsdir.messages()) == 0
    url = 'https://json.aspsms.com/SendSimpleTextSMS'
    json = {
        'UserName': 'username',
        'Password': 'password',
        'Originator': 'Privatim',
        'Recipients': ['+410000000'],
        'MessageText': 'My message'
    }
    post.assert_called_with(url, json=json)
