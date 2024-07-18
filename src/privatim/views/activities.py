from datetime import datetime, time
from zoneinfo import ZoneInfo
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from privatim.models import Consultation, Meeting, Tag
from privatim.models.comment import Comment
from privatim.i18n import _
from privatim.forms.filter_form import FilterForm, render_filter_field


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from ..types import RenderData


def activities_view(request: 'IRequest') -> 'RenderData':
    """Display all activities in the system. (It's the landing page.)"""
    session = request.dbsession
    form = FilterForm(request)
    items: list[Consultation | Meeting | Comment] = []
    include_consultations = True
    include_meetings = True
    include_comments = True

    if request.method == 'POST' and form.validate():
        include_consultations = form.consultation.data
        include_meetings = form.meeting.data
        include_comments = form.comment.data

    start_datetime = None
    end_datetime = None

    if form.start_date.data:
        start_datetime = datetime.combine(
            form.start_date.data, time.min, tzinfo=ZoneInfo("UTC")
        )

    if form.end_date.data:
        end_datetime = datetime.combine(
            form.end_date.data, time.max, tzinfo=ZoneInfo("UTC")
        )

    if include_consultations:
        consultation_query = select(Consultation).options(
            joinedload(Consultation.creator),
            joinedload(Consultation.secondary_tags),
        )
        if start_datetime:
            consultation_query = consultation_query.filter(
                Consultation.updated >= start_datetime
            )
        if end_datetime:
            consultation_query = consultation_query.filter(
                Consultation.updated <= end_datetime
            )
        if form.canton.data and form.canton.data != 'all':
            consultation_query = consultation_query.filter(
                Consultation.secondary_tags.any(Tag.name == form.canton.data)
            )

        items.extend(
            session.execute(consultation_query).unique().scalars().all()
        )

    if include_meetings:
        meeting_query = select(Meeting).options(joinedload(Meeting.attendees))
        if start_datetime:
            meeting_query = meeting_query.filter(
                Meeting.updated >= start_datetime
            )
        if end_datetime:
            meeting_query = meeting_query.filter(
                Meeting.updated <= end_datetime
            )
        items.extend(session.execute(meeting_query).unique().scalars().all())

    if include_comments:
        comment_query = select(Comment)
        if start_datetime:
            comment_query = comment_query.filter(
                Comment.updated >= start_datetime
            )
        if end_datetime:
            comment_query = comment_query.filter(
                Comment.updated <= end_datetime
            )
        items.extend(session.execute(comment_query).unique().scalars().all())

    items.sort(key=lambda x: x.updated)

    return {
        'activities': items,
        'title': _('Activities'),
        'show_add_button': False,
        'filter_form': form,
        'show_filter': True,
        'render_filter_field': render_filter_field,
    }
