from __future__ import annotations
from datetime import datetime, time
from sqlalchemy import select
from pyramid.httpexceptions import HTTPFound
from sqlalchemy.orm import joinedload
from privatim.mail.exceptions import InconsistentChain
from privatim.models import Consultation, Meeting
from privatim.i18n import _
from privatim.forms.filter_form import FilterForm


from typing import TYPE_CHECKING, Any, Literal, TypedDict
from collections.abc import Iterable
if TYPE_CHECKING:
    from sqlalchemy import Select
    from pyramid.interfaces import IRequest
    from privatim.orm import FilteredSession
    from privatim.models import User
    from sqlalchemy.orm import InstrumentedAttribute
    from privatim.types import RenderDataOrRedirect

    class ActivityDict(TypedDict):
        type: Literal['update', 'creation']
        object: Consultation | Meeting
        timestamp: datetime
        user: 'User | None'
        title: str
        route_url: str
        id: int
        icon_class: str
        content: dict[str, str]
        has_files: bool


def maybe_apply_date_filter(
    query: 'Select[Any]',
    start_datetime: datetime | None,
    end_datetime: datetime | None,
    datetime_column: 'InstrumentedAttribute[datetime]'
) -> 'Select[Any]':
    """
    Apply start and end date filters to a given query.
    """
    if start_datetime:
        query = query.filter(datetime_column >= start_datetime)
    if end_datetime:
        query = query.filter(datetime_column <= end_datetime)
    return query


def _get_activity_title(activity: Meeting, is_update: bool) -> str:
    """Get the appropriate title for an activity."""
    assert isinstance(activity, Meeting)
    obj_type = activity.__class__.__name__

    if obj_type == 'Meeting':
        return _('Meeting Updated') if is_update else _('Meeting Scheduled')
    return ''


def activity_to_dict(
        activity: Any, session: 'FilteredSession'
) -> 'ActivityDict':
    """Convert any activity object into a consistent dictionary format."""

    obj_type = activity.__class__.__name__

    # Special handling for Consultation due to versioning
    if obj_type == 'Consultation':
        latest_consultation = activity.get_latest_version(session)
        is_creation = activity.previous_version is None

        has_files = bool(activity.files)
        return {
            'type': 'creation' if is_creation else 'update',
            'object': activity,
            'timestamp': activity.created,
            'user': activity.creator if is_creation else activity.editor,
            'has_files': has_files,
            'title': (
                _('Consultation Added')
                if is_creation
                else _('Consultation Updated')
            ),
            'route_url': 'consultation',
            'id': latest_consultation.id,
            'icon_class': _get_icon_class(obj_type),
            'content': _get_activity_content(activity),
        }

    # Normal handling for other types (Meetings)
    is_update = activity.updated != activity.created
    has_files = bool(activity.files)  # Check if the meeting has files
    return {
        'type': 'update' if is_update else 'creation',
        'object': activity,
        'timestamp': activity.updated if is_update else activity.created,
        'user': getattr(activity, 'editor', None) if is_update else getattr(
            activity, 'creator', None),
        'has_files': has_files,
        'title': _get_activity_title(activity, is_update),
        'route_url': obj_type.lower(),
        'id': activity.id,
        'icon_class': _get_icon_class(obj_type),
        'content': _get_activity_content(activity),
    }


def _get_icon_class(obj_type: str) -> str:
    """Get the appropriate icon class for an activity type."""
    icons = {
        'Meeting': 'fas fa-users',
        'Consultation': 'fas fa-file-alt',
    }
    return icons.get(obj_type, '')


def _get_activity_content(activity: Any) -> dict[str, str]:
    """Get the appropriate content for an activity."""
    obj_type = activity.__class__.__name__

    if obj_type == 'Consultation':
        return {
            'title': (
                activity.title[:100] + '...'
                if len(activity.title) > 100
                else activity.title
            )
        }
    elif obj_type == 'Meeting':
        return {'name': activity.name, 'time': activity.time}
    return {}


def get_activities(session: 'FilteredSession') -> list['ActivityDict']:
    """Return all activities in a consistent dictionary format."""

    # fixme: This is duplicated below, should be refactored (well, almost
    #  duplicated)
    def get_consultations() -> Iterable[Consultation]:
        with session.no_consultation_filter():
            return (
                session.execute(
                    select(Consultation)
                    .options(
                        joinedload(Consultation.creator),
                        joinedload(Consultation.previous_version),
                    )
                    .order_by(Consultation.created.desc())
                )
                .scalars()
                .unique()
            )

    def get_meetings() -> Iterable[Meeting]:
        return (
            session.execute(select(Meeting).order_by(Meeting.updated.desc()))
            .scalars()
            .unique()
        )

    activities = []

    # Get all activities and convert them to dictionaries
    for consultation in get_consultations():
        try:
            res = activity_to_dict(consultation, session)
            activities.append(res)
        except InconsistentChain:
            pass

    for meeting in get_meetings():
        activities.append(activity_to_dict(meeting, session))

    # Sort by timestamp
    activities.sort(key=lambda x: x['timestamp'], reverse=True)

    return activities


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
            return {
                'title': _('Activities'),
                'activities': get_activities(session),
                'form': form,
            }

    if request.method == 'POST' and form.validate():
        query_params = {
            'consultation': str(form.consultation.data),
            'meeting': str(form.meeting.data),
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

    activities_data: list[ActivityDict] = []
    # Get filtered consultations
    if include_consultations:
        with session.no_consultation_filter():
            consultation_query = select(Consultation).options(
                joinedload(Consultation.creator),
                joinedload(Consultation.previous_version),
            )
            consultation_query = maybe_apply_date_filter(
                consultation_query,
                start_datetime,
                end_datetime,
                Consultation.created,
            )

            # fixme: be more robust to Excpetions due to inconsistent chain
            activities_data.extend(
                activity_to_dict(consultation, session)
                for consultation in session.execute(consultation_query)
                .unique()
                .scalars()
                .all()
            )

    # Get filtered meetings
    if include_meetings:
        meeting_query = select(Meeting)
        meeting_query = maybe_apply_date_filter(
            meeting_query, start_datetime, end_datetime, Meeting.updated
        )
        activities_data.extend(
            activity_to_dict(me, session)
            for me in session.execute(meeting_query).unique().scalars().all()
        )

    # Sort all items by their timestamp
    activities_data.sort(key=lambda x: x['timestamp'], reverse=True)
    return {
        'title': _('Activities'),
        'form': form,
        'activities': activities_data,
    }
