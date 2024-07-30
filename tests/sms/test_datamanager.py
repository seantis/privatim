import hashlib
import json
import os
import transaction

from privatim.sms.datamanager import SMSDataManager


def test_send_sms(smsdir):
    transaction.begin()

    data = {
        'Originator': 'Privatim',
        'Recipients': ['+4100000000'],
        'MessageText': 'Message',
    }
    content = json.dumps(data)
    content = content.encode('utf-8')
    filename = hashlib.sha224(content).hexdigest()
    path = os.path.join(smsdir.path, f'{filename}.json')

    SMSDataManager.send_sms(content, path)

    trans = transaction.get()
    dm = trans._resources[0]
    assert dm.data == content
    assert dm.path == path


def test_commit(smsdir):
    transaction.begin()

    data = {
        'Originator': 'Privatim',
        'Recipients': ['+4100000000'],
        'MessageText': 'Message',
    }
    content = json.dumps(data)
    content = content.encode('utf-8')
    filename = hashlib.sha224(content).hexdigest()
    path = os.path.join(smsdir.path, f'{filename}.json')

    dm = SMSDataManager(transaction.manager, content, path)
    assert len(smsdir.messages()) == 0

    dm.commit(None)
    assert len(smsdir.messages()) == 0

    dm.tpc_finish(None)
    assert len(smsdir.messages()) == 1
