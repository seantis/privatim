from __future__ import annotations
from zope.interface import Interface


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from collections.abc import Sequence


class ISMSGateway(Interface):

    def send(
            receivers: 'Sequence[str]',
            content: str,
            sender: str = 'Privatim'
    ) -> None:
        """
        Send SMS containing content to receivers
        """
