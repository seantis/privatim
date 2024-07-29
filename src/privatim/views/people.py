from sqlalchemy import nullslast
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select
from markupsafe import Markup

from privatim.utils import strip_p_tags
from privatim.models import User


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
        ).scalars()
    )

    return {
        'people': people,
    }


def person_view(context: User, request: 'IRequest') -> 'RenderData':
    session = request.dbsession
    stmt = (
        select(User)
        .options(
            selectinload(User.comments),
            selectinload(User.consultations),
        )
        .filter_by(id=context.id)
    )
    user: User = session.execute(stmt).scalar_one()

    meetings_dict = [
        {
            'name': Markup(strip_p_tags(meeting.name)),
            'url': request.route_url('meeting', id=meeting.id)
        } for meeting in user.meetings
    ]

    consultation_dict = [
        {
            'title': Markup(strip_p_tags(consultation.title)),
            'url': request.route_url('consultation', id=consultation.id)
        } for consultation in user.consultations
    ]

    return {
        'user': user,
        'meeting_urls': meetings_dict,
        'consultation_urls': consultation_dict
    }
