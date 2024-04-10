from uuid import UUID
from pyramid.httpexceptions import HTTPNotFound


from typing import TypeVar
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass

_M = TypeVar('_M', bound='Base')


def create_uuid_factory(cls: type[_M]) -> 'Callable[[IRequest], _M]':
    def route_factory(request: 'IRequest') -> _M:

        session = request.dbsession
        matchdict = request.matchdict
        uuid = matchdict.get('id', None)

        if not uuid:
            raise HTTPNotFound()

        try:
            UUID(uuid)
        except ValueError:
            raise HTTPNotFound() from None

        result = session.get(cls, uuid)
        if not result:
            raise HTTPNotFound()
        return result
    return route_factory
