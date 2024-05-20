from privatim.models import Consultation

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from ..types import RenderData


def activities_overview(request: 'IRequest') -> 'RenderData':
    """ Display all activities in the system. (It's the landing page.)"""

    session = request.dbsession
    consultations = session.query(Consultation).all()

    return {'consultations': consultations}
