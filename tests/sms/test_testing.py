from zope.interface.verify import verifyClass

from privatim.sms.interfaces import ISMSGateway
from privatim.testing import DummySMSGateway


def test_interface():
    assert ISMSGateway.implementedBy(DummySMSGateway)
    assert verifyClass(ISMSGateway, DummySMSGateway)


def test_send():
    gateway = DummySMSGateway()
    assert gateway.messages == []

    gateway.send(receivers=['+4100000000'], content='My message')
    assert len(gateway.messages) == 1
    message = gateway.messages[0]
    assert message.receiver == '+4100000000'
    assert message.content == 'My message'
    assert message.sender == 'Privatim'
