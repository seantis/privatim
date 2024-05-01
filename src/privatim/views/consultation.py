from privatim.models import Consultation


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest


def consultation_view(context: Consultation, request: 'IRequest') -> dict:
    consultation = context
    return {'consultation': consultation}
