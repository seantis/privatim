from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest



def group_view(request: 'IRequest'):

    return {'groups': ''}
