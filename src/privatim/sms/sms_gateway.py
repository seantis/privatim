from __future__ import annotations
import hashlib
import json
import os
from zope.interface import implementer

from privatim.sms.datamanager import SMSDataManager
from privatim.sms.interfaces import ISMSGateway


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from collections.abc import Sequence


@implementer(ISMSGateway)
class ASPSMSGateway:

    smsdir: str

    def __init__(self, smsdir: str):
        self.smsdir = smsdir

    def send(
            self,
            receivers: Sequence[str],
            content: str,
            sender: str = 'Privatim'
    ) -> None:

        if not self.smsdir:
            raise Exception('sms.queue_path config variable not set.')

        if not os.path.exists(self.smsdir):
            os.makedirs(self.smsdir)

        receivers = [r.replace(' ', '') for r in receivers]

        data = {
            'Originator': sender,
            'Recipients': receivers,
            'MessageText': content,
        }

        content = json.dumps(data)
        encoded_content = content.encode('utf-8')
        filename = hashlib.sha224(encoded_content).hexdigest()
        path = path = os.path.join(self.smsdir, f'{filename}.json')
        SMSDataManager.send_sms(encoded_content, path)
