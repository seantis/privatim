from .root_factory import root_factory
from .uuid_factory import create_uuid_factory
from privatim.models import WorkingGroup, Consultation

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.models.root import Root


_group_factory = create_uuid_factory(WorkingGroup)
_consultation_factory = create_uuid_factory(Consultation)


def consultation_factory(request: 'IRequest') -> 'WorkingGroup | Root':
    if request.matchdict.get('id', None) is None:
        return root_factory(request)

    return _consultation_factory(request)


def working_group_factory(request: 'IRequest') -> 'WorkingGroup | Root':
    if request.matchdict.get('id', None) is None:
        return root_factory(request)

    return _group_factory(request)


__all__ = ('working_group_factory', 'root_factory')
