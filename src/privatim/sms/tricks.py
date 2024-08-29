import os
from watchdog.tricks import Trick

from privatim.sms.delivery import QueuedSMSDelivery


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from watchdog.events import FileSystemEvent


class SMSDeliveryTrick(Trick):

    smsdir: str | None
    delivery: QueuedSMSDelivery | None

    def __init__(
            self,
            smsdir: str,
            username: str = '',
            password: str = ''  # nosec:B107
    ):
        self.smsdir = None
        self.delivery = None
        if os.path.exists(smsdir):
            self.smsdir = os.path.join(os.path.abspath(smsdir), '')
            self.delivery = QueuedSMSDelivery(
                self.smsdir,
                username,
                password,
            )

        super().__init__(
            patterns=['*.json'],
            ignore_patterns=['*.sending-*', '*.rejected-*'],
            ignore_directories=True
        )

        # Send all pending messages on service start
        if self.delivery is not None:
            self.delivery.send_messages()

    def in_smsdir(self, path: str) -> bool:
        if self.smsdir is None:
            return False
        return os.path.abspath(path).startswith(self.smsdir)

    def on_created(self, event: 'FileSystemEvent') -> None:
        if self.delivery is None:
            return

        src_path = str(event.src_path)

        if not self.in_smsdir(src_path):
            return

        self.delivery._send_message(src_path)
