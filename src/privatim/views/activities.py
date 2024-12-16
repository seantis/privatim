from datetime import datetime, time
from zoneinfo import ZoneInfo
from sqlalchemy import select
from pyramid.httpexceptions import HTTPFound
from sqlalchemy.orm import joinedload
from privatim.models import Consultation, Meeting
from privatim.models.comment import Comment
from privatim.i18n import _
from privatim.forms.filter_form import FilterForm


from typing import TYPE_CHECKING, Any, Literal, TypedDict, Iterable
if TYPE_CHECKING:
    from sqlalchemy import Select
    from pyramid.interfaces import IRequest
    from privatim.orm import FilteredSession
    from privatim.models import User
    from sqlalchemy.orm import InstrumentedAttribute
    from privatim.types import RenderDataOrRedirect

    class ActivityDict(TypedDict):
        type: Literal['update', 'creation']
        object: Consultation | Meeting | Comment
        timestamp: datetime
        user: 'User | None'
        title: str
        route_url: str
        id: int
        icon_class: str
        content: dict[str, str]


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


def _get_activity_title(activity: Comment | Meeting, is_update: bool) -> str:
    """Get the appropriate title for an activity."""
    assert isinstance(activity, (Comment, Meeting))
    obj_type = activity.__class__.__name__

    if obj_type == 'Meeting':
        return _('Meeting Updated') if is_update else _('Meeting Scheduled')
    elif obj_type == 'Comment':
        return _('Comment Updated') if is_update else _('Comment Added')
    return ''


def activity_to_dict(activity: Any) -> 'ActivityDict':
    """Convert any activity object into a consistent dictionary format."""

    obj_type = activity.__class__.__name__

    # Special handling for Consultation due to versioning
    if obj_type == 'Consultation':
        is_creation = activity.previous_version is None

        return {
            'type': 'creation' if is_creation else 'update',
            'object': activity,
            'timestamp': activity.created,
            'user': activity.creator if is_creation else activity.editor,
            'title': (
                _('Consultation Added')
                if is_creation
                else _('Consultation Updated')
            ),
            'route_url': obj_type.lower(),
            'id': activity.id,
            'icon_class': _get_icon_class(obj_type),
            'content': _get_activity_content(activity),
        }

    # Normal handling for other types (Meetings, Comments)
    is_update = activity.updated != activity.created
    return {
        'type': 'update' if is_update else 'creation',
        'object': activity,
        'timestamp': activity.updated if is_update else activity.created,
        'user': getattr(activity, 'editor', None) if is_update else getattr(
            activity, 'creator', None),
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
        'Comment': 'fas fa-comment',
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
    elif obj_type == 'Comment':
        return {
            'content': (
                activity.content[:100] + '...'
                if len(activity.content) > 100
                else activity.content
            )
        }
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
                        joinedload(Consultation.previous_version),  # Add this
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

    activities = []

    # Get all activities and convert them to dictionaries
    for consultation in get_consultations():
        # if "Umwelt Herbst" in consultation.title:
        #     breakpoint()
        activities.append(activity_to_dict(consultation))

    for meeting in get_meetings():
        activities.append(activity_to_dict(meeting))

    for comment in get_comments():
        activities.append(activity_to_dict(comment))

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
                'form': form,
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
            activities_data.extend(
                activity_to_dict(consultation)
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
            activity_to_dict(me)
            for me in session.execute(meeting_query).unique().scalars().all()
        )

    # Get filtered comments
    if include_comments:
        comment_query = (
            select(Comment)
            .options(joinedload(Comment.user))
            .filter(~Comment.deleted)
        )
        comment_query = maybe_apply_date_filter(
            comment_query, start_datetime, end_datetime, Comment.updated
        )
        activities_data.extend(
            activity_to_dict(co)
            for co in session.execute(comment_query).unique().scalars().all()
        )

    # Sort all items by their timestamp
    activities_data.sort(key=lambda x: x['timestamp'], reverse=True)
    return {
        'title': _('Activities'),
        'form': form,
        'activities': activities_data,
    }
