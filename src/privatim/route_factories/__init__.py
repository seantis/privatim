from .root_factory import root_factory
from .uuid_factory import create_uuid_factory
from privatim.models import WorkingGroup, Consultation, User, Meeting

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.models.root import Root


_group_factory = create_uuid_factory(WorkingGroup)
_consultation_factory = create_uuid_factory(Consultation)
_person_factory = create_uuid_factory(User)
_meeting_factory = create_uuid_factory(Meeting)


def consultation_factory(request: 'IRequest') -> 'Consultation | Root':
    if request.matchdict.get('id', None) is None:
        return root_factory(request)

    return _consultation_factory(request)


def working_group_factory(request: 'IRequest') -> 'WorkingGroup | Root':
    if request.matchdict.get('id', None) is None:
        return root_factory(request)

    return _group_factory(request)


def meeting_factory(request: 'IRequest') -> 'Meeting | Root':
    if request.matchdict.get('id', None) is None:
        return root_factory(request)

    return _meeting_factory(request)

def person_factory(request: 'IRequest') -> 'User | Root':

    if request.matchdict.get('id', None) is None:
        return root_factory(request)

    return _person_factory(request)


__all__ = (
    'working_group_factory',
    'person_factory',
    'consultation_factory',
    'root_factory',
)
