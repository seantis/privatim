from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.models import Consultation


def consultation_view(
    context: 'Consultation', request: 'IRequest'
) -> dict[str, 'Consultation']:
    return {'consultation': context}
