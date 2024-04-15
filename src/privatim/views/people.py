from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.types import RenderData


def people_view(request: 'IRequest') -> 'RenderData':
    """ Simple view to display all people ."""

    return {'people': ''}
