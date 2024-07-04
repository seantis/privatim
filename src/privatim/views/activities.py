from sqlalchemy import select, union_all, desc, cast, String, literal
from privatim.models import Consultation, Meeting
from privatim.i18n import _


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from ..types import RenderData


def activities_view(request: 'IRequest') -> 'RenderData':
    """ Display all activities in the system. (It's the landing page.)"""

    session = request.dbsession
    consultation_stmt = select(
        Consultation.id.label('id'),
        Consultation.created.label('timestamp'),
        cast(literal("'consultation'"), String).label('type')
    )
    meeting_stmt = select(
        Meeting.id.label('id'),
        Meeting.time.label('timestamp'),
        cast(literal("'meeting'"), String).label('type')
    )
    union_stmt = union_all(consultation_stmt, meeting_stmt)

    # sort all
    ordered_union_stmt = select(
        union_stmt.c.id, union_stmt.c.timestamp, union_stmt.c.type
    ).order_by(desc('timestamp'))
    result = session.execute(ordered_union_stmt).fetchall()

    activities = [
        (
            session.get(Consultation, row.id)
            if row.type == "'consultation'"
            else session.get(Meeting, row.id)
        )
        for row in result
    ]

    return {
        'activities': activities,
        'title': _('Activities'),
        'show_add_button': False,
    }
