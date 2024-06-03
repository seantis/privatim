from sqlalchemy import select, desc, union_all, literal_column
from privatim.models import Consultation, Meeting
from privatim.i18n import _


from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from ..types import RenderData
    from sqlalchemy import Select
    from datetime import datetime


def activities_view(request: 'IRequest') -> 'RenderData':
    """ Display all activities in the system. (It's the landing page.)"""

    session = request.dbsession
    consultation_stmt: 'Select[tuple[str, datetime, Any]]' = select(
        Consultation.id.label('id'),
        Consultation.created.label('timestamp'),
        literal_column("'consultation'").label('type')
    )

    meeting_stmt: 'Select[Any]' = select(
        Meeting.id.label('id'),
        Meeting.time.label('timestamp'),
        literal_column("'meeting'").label('type')
    )

    union_stmt = union_all(consultation_stmt, meeting_stmt)
    ordered_union_stmt = select(
        union_stmt.c.id, union_stmt.c.timestamp, union_stmt.c.type
    ).order_by(desc('timestamp'))

    result = session.execute(ordered_union_stmt).fetchall()
    consultation_ids = [row.id for row in result if row.type == 'consultation']
    meeting_ids = [row.id for row in result if row.type == 'meeting']

    consultations = (
        session.query(Consultation)
        .filter(Consultation.id.in_(consultation_ids))
        .all()
    )
    meetings = session.query(Meeting).filter(Meeting.id.in_(meeting_ids)).all()

    # Create a dictionary for quick lookup
    consultation_dict = {
        consultation.id: consultation for consultation in consultations
    }
    meeting_dict = {meeting.id: meeting for meeting in meetings}

    activities: list[Consultation | Meeting] = []
    for row in result:
        if row.type == 'consultation':
            activities.append(consultation_dict[row.id])
        elif row.type == 'meeting':
            activities.append(meeting_dict[row.id])

    return {
        'activities': activities,
        'title': _('Activities'),
        'show_add_button': False,
    }
