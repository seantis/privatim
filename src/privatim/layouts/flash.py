from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest

    from privatim.types import RenderData


def flash(context: object, request: IRequest) -> RenderData:
    messages = request.session.pop_flash()
    if not messages:
        return {}

    return {
        'messages': messages
    }
