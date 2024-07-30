import hashlib
import json
import os
import pytest
import transaction
from pyramid import testing


class Message:

    __slots__ = ('receivers', 'content', 'sender')

    def __init__(self, receivers, content, sender):
        self.receivers = receivers
        self.content = content
        self.sender = sender


class TestingSMSdir:

    def __init__(self, dirname):
        self.path = dirname

    def filenames(self):
        return [
            os.path.join(self.path, x) for x in os.listdir(self.path)
            if '.sending-' not in x and '.rejected-' not in x
        ]

    def messages(self):
        messages = []
        for filename in self.filenames():

            with open(filename, 'r') as fd:
                data = json.load(fd)

            content = data['MessageText']
            receivers = data['Recipients']
            sender = data['Originator']

            messages.append(Message(receivers, content, sender))

        return messages


class Gateway:

    def __init__(self, smsdir):
        self.smsdir = smsdir

    def send(self, receivers, content, sender='Privatim'):

        data = {
            'Originator': sender,
            'Recipients': receivers,
            'MessageText': content,
        }
        content = json.dumps(data)
        content = content.encode('utf-8')
        filename = hashlib.sha224(content).hexdigest()
        path = path = os.path.join(self.smsdir, f'{filename}.json')
        with open(path, 'wb') as fd:
            fd.write(content)


@pytest.fixture
def config():
    config = testing.setUp()
    yield config
    testing.tearDown()
    transaction.abort()


@pytest.fixture
def smsdir(tmpdir):
    directory = tmpdir.mkdir('smsdir')
    path = str(directory)
    maildir = TestingSMSdir(path)
    return maildir


@pytest.fixture
def gateway(smsdir):
    gateway = Gateway(smsdir.path)
    return gateway
