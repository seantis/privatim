import transaction
from zope.interface.verify import verifyClass

from privatim.sms.interfaces import ISMSGateway
from privatim.sms.sms_gateway import ASPSMSGateway


def test_interface():
    assert ISMSGateway.implementedBy(ASPSMSGateway)
    assert verifyClass(ISMSGateway, ASPSMSGateway)


def test_send(smsdir):
    gateway = ASPSMSGateway(smsdir.path)
    gateway.send(receivers=['+41000000000'], content='My message')
    assert smsdir.messages() == []

    transaction.commit()
    messages = smsdir.messages()
    assert len(messages) == 1
    message = messages[0]
    assert message.receivers == ['+41000000000']
    assert message.content == 'My message'
    assert message.sender == 'Privatim'


def test_send_encoding(smsdir):
    gateway = ASPSMSGateway(smsdir.path)
    gateway.send(receivers=['+41000000000'], content='Viel Gl\xfcck')
    transaction.commit()
    messages = smsdir.messages()
    assert len(messages) == 1
    message = messages[0]
    assert message.receivers == ['+41000000000']
    assert message.content == 'Viel Gl\xfcck'
    assert message.sender == 'Privatim'


def test_send_number_format(smsdir):
    gateway = ASPSMSGateway(smsdir.path)
    gateway.send(receivers=['+41 77 000 00 00'], content='Message')
    transaction.commit()
    messages = smsdir.messages()
    assert len(messages) == 1
    message = messages[0]
    assert message.receivers == ['+41770000000']
    assert message.content == 'Message'
    assert message.sender == 'Privatim'


def test_send_sender(smsdir):
    gateway = ASPSMSGateway(smsdir.path)
    gateway.send(receivers=['+41000000000'], content='Test', sender='Test')
    transaction.commit()
    messages = smsdir.messages()
    assert len(messages) == 1
    message = messages[0]
    assert message.receivers == ['+41000000000']
    assert message.content == 'Test'
    assert message.sender == 'Test'
