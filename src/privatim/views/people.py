from sqlalchemy import nullslast
from privatim.models import User
from sqlalchemy.future import select


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.types import RenderData


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

    return {
        'people': people,
    }


def person_view(context: User, request: 'IRequest') -> 'RenderData':

    return {
        'person': context
    }
