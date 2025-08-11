from datetime import datetime, time
from zoneinfo import ZoneInfo
from sqlalchemy import select
from pyramid.httpexceptions import HTTPFound
from sqlalchemy.orm import joinedload
from privatim.mail.exceptions import InconsistentChain
from privatim.models import Consultation, Meeting, MeetingEditEvent
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
        object: Consultation | Meeting
        timestamp: datetime
        user: 'User | None'
        title: str
        route_url: str
        id: int
        icon_class: str
        content: dict[str, Any]


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


def activity_to_dict(
    activity: Any, session: 'FilteredSession'
) -> 'ActivityDict':
    """Convert any activity object into a consistent dictionary format."""

    # NOTE: This file contains numerous type-checking conditionals that would
    # benefit from polymorphic refactoring. Consider moving this logic to the
    # respective `Consultation` or `MeetingEditEvent` classes.

    obj_type = activity.__class__.__name__
    if obj_type == 'MeetingEditEvent':
        content: dict[str, Any] = {'name': activity.meeting.name,
                                   'time': activity.meeting.created}

        if (activity.event_type == 'file_update'
                or activity.event_type == 'update'):
            content.update({
                'added_files': activity.added_files,
                'removed_files': activity.removed_files
            })
        return {
            'type': 'creation' if activity.event_type == 'creation'
            else 'update',
            'object': activity.meeting,
            'timestamp': activity.created,
            'user': activity.creator,
            'title': activity.get_label_event_type(),
            'route_url': 'meeting',
            'id': activity.meeting.id,
            'icon_class': _get_icon_class('Meeting', activity.event_type),
            'content': content,
        }

    # Special handling for Consultation due to versioning
    if obj_type == 'Consultation':
        with session.no_consultation_filter():
            latest_consultation = activity.get_latest_version(session)
            is_creation = activity.previous_version is None

            content: dict[str, Any] = {
                'title': (
                    activity.title[:100] + '...'
                    if len(activity.title) > 100
                    else activity.title
                )
            }
            title = (
                _('Consultation Added')
                if is_creation
                else _('Consultation Updated')
            )
            icon_class = _get_icon_class(obj_type)

            if not is_creation:
                added_files = sorted(activity.added_files or [])
                removed_files = sorted(activity.removed_files or [])
                other_fields_changed = (
                    activity.title != activity.previous_version.title
                    or activity.description != activity.previous_version.description
                    or activity.recommendation != activity.previous_version.recommendation
                    or activity.evaluation_result != activity.previous_version.evaluation_result
                    or activity.decision != activity.previous_version.decision
                    or activity.status != activity.previous_version.status
                    or set(activity.secondary_tags) != set(
                        activity.previous_version.secondary_tags
                    )
                )

                if added_files or removed_files:
                    content.update({
                        'added_files': added_files,
                        'removed_files': removed_files
                    })
                    if not other_fields_changed:
                        title = _('Consultation Files Updated')
                        icon_class = _get_icon_class('Meeting', 'file_update')

            return {
                'type': 'creation' if is_creation else 'update',
                'object': activity,
                'timestamp': activity.created,
                'user': activity.creator if is_creation else activity.editor,
                'title': title,
                'route_url': 'consultation',
                'id': latest_consultation.id,
                'icon_class': icon_class,
                'content': content,
            }

    # Fallback for any other type, though we expect none.
    raise TypeError(f'Unsupported activity type: {obj_type}')


def _get_icon_class(obj_type: str, event_type: str | None = None) -> str:
    if obj_type == 'Meeting' and event_type == 'file_update':
        return 'fas fa-pencil-alt'
    icons = {
        'Meeting': 'fas fa-users',
        'Consultation': 'fas fa-file-alt',
    }
    return icons.get(obj_type, '')


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

    def get_meeting_edit_events() -> Iterable[MeetingEditEvent]:
        return (
            session.execute(
                select(MeetingEditEvent)
                .options(
                    joinedload(MeetingEditEvent.creator),
                    joinedload(MeetingEditEvent.meeting).joinedload(Meeting.files)
                )
                .order_by(MeetingEditEvent.created.desc())
            )
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

    for meeting_edit_event in get_meeting_edit_events():
        activities.append(activity_to_dict(meeting_edit_event, session))

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

    # main filtering logic begins:
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
        meeting_edit_event_query = (
            select(MeetingEditEvent)
            .options(
                joinedload(MeetingEditEvent.creator),
                joinedload(MeetingEditEvent.meeting).joinedload(Meeting.files)
            )
        )
        meeting_edit_event_query = maybe_apply_date_filter(
            meeting_edit_event_query,
            start_datetime,
            end_datetime,
            MeetingEditEvent.created,
        )
        activities_data.extend(
            activity_to_dict(ma, session)
            for ma in session.execute(meeting_edit_event_query)
            .unique()
            .scalars()
            .all()
        )

    # Sort all items by their timestamp
    activities_data.sort(key=lambda x: x['timestamp'], reverse=True)
    return {
        'title': _('Activities'),
        'form': form,
        'activities': activities_data,
    }
