from privatim.models.attached_document import ConsultationDocument

from .root_factory import root_factory
from .uuid_factory import create_uuid_factory
from privatim.models import AgendaItem
from privatim.models import WorkingGroup, Consultation, User, Meeting

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.models.root import Root


_working_group_factory = create_uuid_factory(WorkingGroup)
_consultation_factory = create_uuid_factory(Consultation)
_person_factory = create_uuid_factory(User)
_meeting_factory = create_uuid_factory(Meeting)
_agenda_item_factory = create_uuid_factory(AgendaItem)


def consultation_factory(request: 'IRequest') -> 'Consultation | Root':
    if request.matchdict.get('id', None) is None:
        return root_factory(request)

    return _consultation_factory(request)


def working_group_factory(request: 'IRequest') -> 'WorkingGroup | Root':

    # if request.matchdict.get('id', None) is None:
    #     return root_factory(request)

    return _working_group_factory(request)


def meeting_factory(request: 'IRequest') -> 'Meeting | Root':
    return _meeting_factory(request)


def agenda_item_factory(request: 'IRequest') -> AgendaItem:
    return _agenda_item_factory


def default_meeting_factory(request: 'IRequest') -> Meeting:
    factory = create_uuid_factory(Meeting)
    return factory(request)


def person_factory(request: 'IRequest') -> 'User | Root':

    if request.matchdict.get('id', None) is None:
        return root_factory(request)

    return _person_factory(request)


consultation_document_factory = create_uuid_factory(
    ConsultationDocument,
    key='consultation_doc_id'
)


__all__ = (
    'working_group_factory',
    'person_factory',
    'consultation_factory',
    'root_factory',
)
