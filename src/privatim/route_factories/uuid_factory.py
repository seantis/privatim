from typing import TypeVar
from uuid import UUID
from pyramid.httpexceptions import HTTPNotFound
from privatim.models import Consultation


from typing import TYPE_CHECKING

from privatim.orm.session import FilteredSession
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


def create_consultation_all_versions_factory(
    key: str = 'id'
) -> 'Callable[[IRequest], Consultation]':
    """Creates a factory specifically for Consultation models.

    Unlike the generic UUID factory, this one manages Consultation versioning
    by automatically redirecting to latest version for any prior (n-1) version.

    This increases robustness, if (by whatever reason) an old version is
    requested, for example by a bookmark.
    """

    def route_factory(request: 'IRequest') -> Consultation:
        session: FilteredSession = request.dbsession
        matchdict = request.matchdict
        uuid = matchdict.get(key, None)
        if not uuid:
            raise HTTPNotFound()
        try:
            UUID(uuid)
        except ValueError:
            raise HTTPNotFound() from None

        with session.no_consultation_filter():
            consultation = session.get(Consultation, uuid)
            if not consultation:
                raise HTTPNotFound()

            return consultation.get_latest_version(session)

    return route_factory
