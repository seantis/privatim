from typing import TYPE_CHECKING
from typing import TypeVar
from uuid import UUID

from pyramid.httpexceptions import HTTPNotFound

if TYPE_CHECKING:
    from collections.abc import Callable
    from pyramid.interfaces import IRequest

    from privatim.orm import Base

_M = TypeVar('_M', bound='Base')


def create_uuid_factory(
        cls: type[_M],
        key: str = 'id'
) -> 'Callable[[IRequest], _M]':
    def route_factory(request: 'IRequest') -> _M:

        session = request.dbsession
        matchdict = request.matchdict
        uuid = matchdict.get(key, None)

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
