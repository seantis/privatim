from sqlalchemy import nullslast
from sqlalchemy.orm import selectinload

from privatim.models import User
from sqlalchemy.future import select


from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.types import RenderData
    from sqlalchemy.orm import Session
    from privatim.models import Consultation, Meeting


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


def query_user_details(session: 'Session', user_id: str) -> User:
    stmt = (
        select(User)
        .options(
            selectinload(User.comments),
            selectinload(User.meetings),
            selectinload(User.consultations),
        )
        .filter_by(id=user_id)
    )
    return session.execute(stmt).scalar_one()


def person_view(context: User, request: 'IRequest') -> 'RenderData':
    session = request.dbsession

    user = query_user_details(session, context.id)

    def generate_urls(
        items: 'Sequence[Consultation | Meeting]', name: str
    ) -> 'list[tuple[Consultation | Meeting, str]]':
        return [(item, request.route_url(name, id=item.id)) for item in items]

    meeting_urls = generate_urls(user.meetings, 'meeting')
    consultation_urls = generate_urls(user.consultations, 'consultation')

    return {
        'user': user,
        'meeting_urls': meeting_urls,
        'consultation_urls': consultation_urls
    }
