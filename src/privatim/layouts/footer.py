from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.types import RenderData


def footer(context: object, request: 'IRequest') -> 'RenderData':

    return {}
