from sqlalchemy import select, union_all, desc, cast, String, literal
from sqlalchemy.orm import joinedload, contains_eager

from privatim.models import Consultation, Meeting, Tag
from privatim.i18n import _
from privatim.forms.filter_form import FilterForm, render_filter_field


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from ..types import RenderData


def activities_view(request: 'IRequest') -> 'RenderData':
    """ Display all activities in the system. (It's the landing page.)"""
    session = request.dbsession
    breakpoint()
    filter_form = FilterForm(request)

    consultation_query = select(Consultation).options(
        joinedload(Consultation.creator),
        joinedload(Consultation.secondary_tags)
    )
    meeting_query = select(Meeting).options(
        joinedload(Meeting.attendees)
    )

    if request.method == 'POST' and filter_form.validate():

        if filter_form.start_date.data is not None:
            consultation_query = consultation_query.filter(
                Consultation.created >= filter_form.start_date.data
            )
            meeting_query = meeting_query.filter(
                Meeting.time >= filter_form.start_date.data
            )
        if filter_form.end_date.data is not None:
            consultation_query = consultation_query.filter(
                Consultation.created <= filter_form.end_date.data
            )
            meeting_query = meeting_query.filter(
                Meeting.time <= filter_form.end_date.data
            )
        # if filter_form.canton.data:
        #     consultation_query = consultation_query.filter(
        #         Consultation.secondary_tags.any(Tag.name == filter_form.canton.data)
        #     )

    consultations = (
        session.execute(consultation_query).unique().scalars().all()
        if filter_form.consultation.data or not filter_form.meeting.data
        else []
    )
    meetings = (
        session.execute(meeting_query).unique().scalars().all()
        if filter_form.meeting.data or not filter_form.consultation.data
        else []
    )

    activities = sorted(
        consultations + meetings,
        key=lambda x: x.created if isinstance(x, Consultation) else x.time,
        reverse=True
    )

    return {
        'activities': activities,
        'title': _('Activities'),
        'show_add_button': False,
        'filter_form': filter_form,
        'show_filter': True,
        'render_filter_field': render_filter_field,
    }
