from typing import TYPE_CHECKING

from privatim.i18n import translate

if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from typing import Literal

    MessageType = Literal[
        'info',
        'warning',
        'error',
        'danger',
        'success'
    ]


class MessageQueue:
    _request: 'IRequest'

    def __init__(self, request: 'IRequest') -> None:
        self._request = request

    def add(self, message: str, typ: 'MessageType' = 'info') -> None:
        if typ == 'error':
            typ = 'danger'
        message = translate(message)
        self._request.session.flash({'type': typ, 'message': message})

    def pop(self) -> list[dict[str, str]]:
        return self._request.session.pop_flash()

    def clear(self) -> None:
        self._request.session.pop_flash()
