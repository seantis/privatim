from datetime import datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import select
from pyramid.httpexceptions import HTTPFound
from sqlalchemy.orm import joinedload
from privatim.models import Consultation, Meeting, Tag
from privatim.models.comment import Comment
from privatim.i18n import _
from privatim.forms.filter_form import FilterForm, render_filter_field


from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy import Select
    from pyramid.interfaces import IRequest
    from privatim.types import RenderDataOrRedirect


def apply_date_filter(
    query: 'Select[Any]',
    start_datetime: datetime | None,
    end_datetime: datetime | None,
    date_column: Any,
) -> 'Select[Any]':
    """
    Apply start and end date filters to a given query.
    """
    if start_datetime:
        query = query.filter(date_column >= start_datetime)
    if end_datetime:
        query = query.filter(date_column <= end_datetime)
    return query


def activities_view(request: 'IRequest') -> 'RenderDataOrRedirect':
    """Display all activities in the system. (It's the landing page.)"""
    session = request.dbsession
    form = FilterForm(request)

    if request.method == 'POST' and form.validate():
        query_params = {
            'consultation': str(form.consultation.data),
            'meeting': str(form.meeting.data),
            'comment': str(form.comment.data),
            'start_date': (
                form.start_date.data.isoformat()
                if form.start_date.data
                else ''
            ),
            'end_date': (
                form.end_date.data.isoformat() if form.end_date.data else ''
            ),
            'canton': form.canton.data,
        }
        return HTTPFound(
            location=request.route_url('activities', _query=query_params)
        )

    include_consultations = (
        False if request.GET.get('consultation') is None else True
    )
    include_meetings = False if request.GET.get('meeting') is None else True
    include_comments = False if request.GET.get('comment') is None else True
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    canton = request.GET.get('canton', 'all')

    if len(request.GET) == 0:
        # default case, no filter. We show meeting and consultations by default
        include_consultations = True
        include_meetings = True

    start_datetime = None
    end_datetime = None
    if start_date:
        start_datetime = datetime.combine(
            datetime.fromisoformat(start_date).date(),
            time.min,
            tzinfo=ZoneInfo("UTC"),
        )
    if end_date:
        end_datetime = datetime.combine(
            datetime.fromisoformat(end_date).date(),
            time.max,
            tzinfo=ZoneInfo("UTC"),
        )

    items: list[Consultation | Meeting | Comment] = []

    # Query construction for Consultations
    if include_consultations:
        consultation_query = select(Consultation).options(
            joinedload(Consultation.creator),
            joinedload(Consultation.secondary_tags),
        )
        consultation_query = apply_date_filter(
            consultation_query,
            start_datetime,
            end_datetime,
            Consultation.updated,
        )
        if canton != 'all':
            consultation_query = consultation_query.filter(
                Consultation.secondary_tags.any(Tag.name == canton)
            )
        items.extend(
            session.execute(consultation_query).unique().scalars().all()
        )

    # Query construction for Meetings
    if include_meetings:
        meeting_query = select(Meeting).options(joinedload(Meeting.attendees))
        meeting_query = apply_date_filter(
            meeting_query, start_datetime, end_datetime, Meeting.updated
        )
        items.extend(session.execute(meeting_query).unique().scalars().all())

    # Query construction for Comments
    if include_comments:
        comment_query = select(Comment).options(joinedload(Comment.user))
        comment_query = apply_date_filter(
            comment_query, start_datetime, end_datetime, Comment.updated
        )
        items.extend(session.execute(comment_query).unique().scalars().all())

    # Sort all items by their 'updated' attribute
    items.sort(key=lambda x: x.updated, reverse=True)
    return {
        'activities': items,
        'title': _('Activities'),
        'show_add_button': False,
        'filter_form': form,
        'show_filter': True,
        'render_filter_field': render_filter_field,
    }
