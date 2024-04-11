from privatim.models import Consultation

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest


def activities_overview(request: 'IRequest'):
    """ Display all activities in the system.
        It's the landing page ."""

    session = request.dbsession
    foo = request.matched_route.name
    consultations = session.query(Consultation)

    return {'consultations': consultations}
