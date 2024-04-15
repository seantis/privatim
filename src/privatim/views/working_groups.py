from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from ..types import RenderData


def group_view(request: 'IRequest') -> 'RenderData':

    return {'groups': ''}
