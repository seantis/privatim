from sqlalchemy import nullslast
from privatim.atoz import AtoZ
from privatim.models import User
from sqlalchemy.future import select


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.types import RenderData
    from collections.abc import Sequence


def people_view(request: 'IRequest') -> 'RenderData':

    session = request.dbsession
    people = (
        session.execute(
            select(User).order_by(
                nullslast(User.last_name),
                nullslast(User.first_name)
            )
        ).scalars().all()
    )

    class AtoZPeople(AtoZ[User]):

        def get_title(self, item: User) -> str:
            return item.fullname

        def get_items(self) -> 'Sequence[User]':
            return people

    return {
        'people': AtoZPeople(request).get_items_by_letter().items(),
    }


def person_view(context: User, request: 'IRequest') -> 'RenderData':

    return {
        'person': context
    }
