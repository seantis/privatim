from unittest.mock import MagicMock
from unittest.mock import patch

from privatim.sms.delivery import QueuedSMSDelivery


@patch('requests.post')
def test_send_messages(post, smsdir, gateway):
    delivery = QueuedSMSDelivery(smsdir.path, 'username', 'password')
    assert len(smsdir.messages()) == 0
    delivery.send_messages()

    post.return_value = MagicMock(
        json=lambda: {'StatusInfo': 'OK', 'StatusCode': '1'}
    )
    gateway.send(receivers=['+410000000'], content='My message')
    assert len(smsdir.messages()) == 1
    delivery.send_messages()
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
def test_send_messages_encoding(post, smsdir, gateway):
    delivery = QueuedSMSDelivery(smsdir.path, 'username', 'password')

    post.return_value = MagicMock(
        json=lambda: {'StatusInfo': 'OK', 'StatusCode': '1'}
    )
    gateway.send(receivers=['+410000000'], content='Viel Gl\xfcck')
    assert len(smsdir.messages()) == 1
    delivery.send_messages()
    assert len(smsdir.messages()) == 0
    url = 'https://json.aspsms.com/SendSimpleTextSMS'
    json = {
        'UserName': 'username',
        'Password': 'password',
        'Originator': 'Privatim',
        'Recipients': ['+410000000'],
        'MessageText': 'Viel Gl\xfcck'
    }
    post.assert_called_with(url, json=json)


@patch('requests.post')
def test_send_messages_sender(post, smsdir, gateway):
    delivery = QueuedSMSDelivery(smsdir.path, 'username', 'password')

    post.return_value = MagicMock(
        json=lambda: {'StatusInfo': 'OK', 'StatusCode': '1'}
    )
    gateway.send(receivers=['+410000023'], content='Test', sender='Test')
    assert len(smsdir.messages()) == 1
    delivery.send_messages()
    assert len(smsdir.messages()) == 0
    url = 'https://json.aspsms.com/SendSimpleTextSMS'
    json = {
        'UserName': 'username',
        'Password': 'password',
        'Originator': 'Test',
        'Recipients': ['+410000023'],
        'MessageText': 'Test'
    }
    post.assert_called_with(url, json=json)


@patch('requests.post')
def test_send_messages_sender_encoding(post, smsdir, gateway):
    delivery = QueuedSMSDelivery(smsdir.path, 'username', 'password')

    post.return_value = MagicMock(
        json=lambda: {'StatusInfo': 'OK', 'StatusCode': '1'}
    )
    gateway.send(receivers=['+410000023'], content='Test', sender='M\xfcller')
    assert len(smsdir.messages()) == 1
    delivery.send_messages()
    assert len(smsdir.messages()) == 0
    url = 'https://json.aspsms.com/SendSimpleTextSMS'
    json = {
        'UserName': 'username',
        'Password': 'password',
        'Originator': 'M\xfcller',
        'Recipients': ['+410000023'],
        'MessageText': 'Test'
    }
    post.assert_called_with(url, json=json)


@patch('requests.post')
def test_send_messages_error(post, smsdir, gateway, caplog):
    delivery = QueuedSMSDelivery(smsdir.path, 'username', 'password')
    post.return_value = MagicMock(json=lambda: {'StatusInfo': 'ERROR'})
    gateway.send(receivers=['+410000000'], content='My message')
    delivery.send_messages()
    assert len(smsdir.messages()) == 1
    assert 'Error while sending SMS' in caplog.text
    msg = 'Sending SMS failed, got: "{\'StatusInfo\': \'ERROR\'}'
    assert msg in caplog.text
