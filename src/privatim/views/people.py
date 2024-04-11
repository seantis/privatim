from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest



def people_view(request: 'IRequest'):
    """ Simple view to display all people ."""

    return {'people': ''}
