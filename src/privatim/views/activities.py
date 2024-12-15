from datetime import datetime, time
from itertools import chain
from zoneinfo import ZoneInfo

from sqlalchemy import select
from pyramid.httpexceptions import HTTPFound
from sqlalchemy.orm import joinedload, QueryableAttribute
from privatim.models import Consultation, Meeting
from privatim.models.comment import Comment
from privatim.i18n import _
from privatim.forms.filter_form import FilterForm


from typing import TYPE_CHECKING, Any, Iterable
if TYPE_CHECKING:
    from sqlalchemy import Select
    from sqlalchemy.orm import Session
    from pyramid.interfaces import IRequest
    from privatim.types import RenderDataOrRedirect, Activity


def maybe_apply_date_filter(
    query: 'Select[Any]',
    start_datetime: datetime | None,
    end_datetime: datetime | None,
    datetime_column: 'QueryableAttribute[datetime]',
) -> 'Select[Any]':
    """
    Apply start and end date filters to a given query.
    """
    if start_datetime:
        query = query.filter(datetime_column >= start_datetime)
    if end_datetime:
        query = query.filter(datetime_column <= end_datetime)
    return query


def get_activities(session: 'Session') -> list[Any]:
    """ Return all activities. """
    def get_consultations() -> Iterable[Consultation]:
        return session.execute(
            select(Consultation)
            .options(
                joinedload(Consultation.creator),
            )
            .order_by(Consultation.updated.desc())
        ).scalars().unique()

    def get_meetings() -> Iterable[Meeting]:
        return session.execute(
            select(Meeting)
            .order_by(Meeting.updated.desc())
        ).scalars().unique()

    def get_comments() -> Iterable[Comment]:
        return (
            session.execute(
                select(Comment)
                .options(joinedload(Comment.user))
                .order_by(Comment.updated.desc())
                .filter(~Comment.deleted)
            )
            .scalars()
            .unique()
        )

    # Combine all activities using itertools.chain
    all_activities = sorted(
        chain(get_consultations(), get_meetings(), get_comments()),
        key=lambda x: x.updated,  # type: ignore[attr-defined]
        reverse=True
    )
    return all_activities


def activities_view(request: 'IRequest') -> 'RenderDataOrRedirect':
    """Display all activities in the system. (It's the landing page.)

    Handle form submission using POST/Redirect/GET design pattern. This
    prevents the browser warning on refresh.
    """

    session = request.dbsession
    form = FilterForm(request)

    has_query_params = any(request.GET)
    if request.method == 'GET':
        if has_query_params:
            form.consultation.data = request.GET.get('consultation') == 'True'
            form.meeting.data = request.GET.get('meeting') == 'True'
            form.comment.data = request.GET.get('comment') == 'True'
            form.start_date.data = (
                datetime.fromisoformat(request.GET['start_date'])
                if request.GET.get('start_date')
                else None
            )
            form.end_date.data = (
                datetime.fromisoformat(request.GET['end_date'])
                if request.GET.get('end_date')
                else None
            )
        else:
            # Default GET response, show everything, no filter.
            form.consultation.data = True
            form.meeting.data = True
            form.comment.data = True
            return {
                'title': _('Activities'),
                'activities': get_activities(session),
                'form': form
            }

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
        }
        return HTTPFound(
            location=request.route_url('activities', _query=query_params)
        )

    include_consultations = form.consultation.data
    include_meetings = form.meeting.data
    include_comments = form.comment.data
    start_date = form.start_date.data
    end_date = form.end_date.data

    start_datetime = (
        datetime.combine(start_date, time.min, tzinfo=ZoneInfo('UTC'))
        if start_date
        else None
    )
    end_datetime = (
        datetime.combine(end_date, time.max, tzinfo=ZoneInfo('UTC'))
        if end_date
        else None
    )

    activities: list[Activity] = []
    if include_consultations:
        consultation_query = select(Consultation).options(
            joinedload(Consultation.creator),
        )
        consultation_query = maybe_apply_date_filter(
            consultation_query,
            start_datetime,
            end_datetime,
            Consultation.updated,
        )
        activities.extend(
            session.execute(consultation_query).unique().scalars().all()
        )

    if include_meetings:
        meeting_query = select(Meeting)
        meeting_query = maybe_apply_date_filter(
            meeting_query, start_datetime, end_datetime, Meeting.updated
        )
        activities.extend(
            session.execute(meeting_query).unique().scalars().all()
        )

    if include_comments:
        comment_query = (
            select(Comment)
            .options(joinedload(Comment.user))
            .filter(~Comment.deleted)
        )

        comment_query = maybe_apply_date_filter(
            comment_query, start_datetime, end_datetime, Comment.updated
        )
        activities.extend(
            session.execute(comment_query).unique().scalars().all()
        )

    # Sort all items by their 'updated' attribute
    activities.sort(key=lambda x: x.updated, reverse=True)
    return {
        'title': _('Activities'),
        'form': form,
        'activities': activities,
    }
