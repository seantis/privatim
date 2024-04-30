from .root_factory import root_factory
from .uuid_factory import create_uuid_factory
from privatim.models import WorkingGroup


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.models.root import Root


group_factory = create_uuid_factory(WorkingGroup)


def working_group_factory(request: 'IRequest') -> 'WorkingGroup | Root':
    if request.matchdict.get('id', None) is None:
        return root_factory(request)

    return group_factory(request)


__all__ = ('working_group_factory',
           'root_factory')
