from __future__ import annotations

import logging
import bleach
from markupsafe import Markup
from pyramid.response import Response
from sqlalchemy import func, select
from privatim.models.association_tables import (
    AttendanceStatus,
    AgendaItemDisplayState,
    AgendaItemStatePreference,
)
from privatim.models.file import SearchableFile
from privatim.reporting.report import (
    MeetingReport,
    ReportOptions,
    HTMLReportRenderer,
    WordReportRenderer,
)
from privatim.utils import datetime_format, dictionary_to_binary
from privatim.controls.controls import Button
from pyramid.httpexceptions import (
    HTTPFound,
    HTTPNotFound,
    HTTPBadRequest,
    HTTPMethodNotAllowed,
)
from privatim.utils import fix_utc_to_local_time
from privatim.forms.meeting_form import (
    MeetingForm,
    sync_meeting_attendance_records,
)
from privatim.models import Meeting, WorkingGroup, MeetingEditEvent
from privatim.i18n import _
from privatim.i18n import translate

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from collections.abc import Sequence
    from pyramid.interfaces import IRequest
    from privatim.models.association_tables import MeetingUserAttendance
    from privatim.types import RenderData, XHRDataOrRedirect
    from privatim.types import MixedDataOrRedirect


log = logging.getLogger('privatim.views')


def meeting_view(
        context: Meeting,
        request: 'IRequest'
) -> 'RenderData':
    """ Displays a single meeting. """
    assert isinstance(context, Meeting)
    session = request.dbsession

    stmt = select(func.count(Meeting.id)).where(
        Meeting.working_group_id == context.working_group.id
    )
    meeting_count = session.execute(stmt).scalar_one()
    disable_copy_button = meeting_count <= 1

    # Get all preferences for this user and these agenda items in one query
    preferences_stmt = (
        select(AgendaItemStatePreference)
        .where(
            AgendaItemStatePreference.user_id == request.user.id,
            AgendaItemStatePreference.agenda_item_id.in_(
                item.id for item in context.agenda_items
            )
        )
    )
    preferences = {
        str(pref.agenda_item_id): pref.state
        for pref in session.execute(preferences_stmt).scalars()
    }

    formatted_time = datetime_format(context.time)
    request.add_action_menu_entries(
        (
            Button(
                url=request.route_url('edit_meeting', id=context.id),
                icon='edit',
                title=_('Edit'),
                css_class='dropdown-item',
                description=_('Edit meeting'),
            ),
            Button(
                title=_('Copy'),
                css_class='dropdown-item',
                url=request.route_url('copy_agenda_item', id=context.id),
                icon='copy',
                description=(
                    translate(_('Copy Agenda Items'))
                    if not disable_copy_button
                    else translate(_('No other meetings to copy from'))
                ),
                disabled=disable_copy_button,
            ),
            Button(
                title=_('Export PDF'),
                css_class='dropdown-item',
                url=request.route_url(
                    'export_meeting_as_pdf_view', id=context.id
                ),
                icon='file-export',
                description=translate(_('Export meeting protocol as PDF')),
            ),
            Button(
                title=_('Export DOCX'),
                css_class='dropdown-item',
                url=request.route_url(
                    'export_meeting_as_docx_view', id=context.id
                ),
                icon='file-word',
                description=translate(_('Export meeting protocol as Word')),
            ),
            Button(
                url=request.route_url('delete_meeting', id=context.id),
                icon='trash',
                title=_('Delete'),
                css_class='dropdown-item',
                description=_('Delete Meeting'),
                modal='#delete-xhr',
                data_item_title=context.name,
            ),
        )
    )

    agenda_items = []
    all_items_expanded = True
    for indx, item in enumerate(context.agenda_items, start=1):
        is_expanded = preferences.get(
            str(item.id),
            AgendaItemDisplayState.COLLAPSED
        ) == AgendaItemDisplayState.EXPANDED

        if not is_expanded:
            all_items_expanded = False
        agenda_items.append(
            {
                'title': Markup(   # nosec: MS001
                    '<strong>{}.</strong> {}'.format(
                        indx, bleach.clean(item.title)
                    )
                ),
                'description': Markup(bleach.clean(
                    item.description)),   # nosec: MS001
                'id': item.id,
                'position': item.position,
                'is_expanded': is_expanded,
                'edit_btn': Button(
                    url=request.route_url('edit_agenda_item', id=item.id),
                    icon='edit',
                    description=_('Edit Agenda Item'),
                ),
                'delete_btn': Button(
                    url=request.route_url('delete_agenda_item', id=item.id),
                    icon='trash',
                    description=_('Delete Agenda Item'),
                    modal='#delete-xhr',
                    data_item_title=item.title,
                ),
            }
        )
    data_sortable_url = request.route_url(
        'sortable_agenda_items',
        id=context.id,
        subject_id='{subject_id}',
        direction='{direction}',
        target_id='{target_id}',
    )
    return {
        'delete_title': _('Delete'),
        'time': formatted_time,
        'meeting': context,
        'meeting_attendees': user_list(
            request, context.attendance_records
        ),
        'agenda_items': agenda_items,
        'sortable_url': data_sortable_url,
        'navigate_back_up': request.route_url(
            'meetings', id=context.working_group.id
        ),
        'expand_all_text': _('Expand All'),
        'collapse_all_text': _('Collapse All'),
        'all_expanded': all_items_expanded,
        'has_agenda_items': bool(agenda_items),
        'documents': [
            {
                'display_filename': doc.filename,  # Use full filename
                'doc_content_type': doc.content_type,
                'download_url': request.route_url('download_file', id=doc.id),
            }
            for doc in context.files
        ],
    }


def user_list(
    request: 'IRequest', users: Sequence['MeetingUserAttendance']
) -> Markup:
    """Returns an HTML list of users with profile pictures, links to their
    profiles, and checkbox on the right, with tooltips."""
    title = translate(_('Attendees:'))
    if not users:
        return Markup('')
    user_items = tuple(
        Markup(
            '<li class="user-list-item d-flex justify-content-between '
            'align-items-center">'
            '<div class="d-flex align-items-center">'
            '<div class="profile-pic-container me-2" style="'
            'width: 24px; height: 24px; overflow: hidden; border-radius: 50%; '
            'display: flex; justify-content: center; align-items: center;">'
            '<img src="{}" alt="{} profile picture" style="'
            'width: 100%; height: 100%; object-fit: cover;">'
            '</div>'
            '<a href="{}" class="mb-1 text-decoration-none">{}</a>'
            '</div>'
            '<div class="form-check" data-bs-toggle="tooltip" title="{}">'
            '<input class="form-check-input fix-checkbox-in-list" '
            'type="checkbox" '
            'value="" '
            'id="attendance-{}" {} disabled>'
            '<label class="form-check-label" for="attendance-{}"></label>'
            '</div>'
            '</li>'
        ).format(
            user.user.profile_pic_download_link(
                request
            ),
            user.user.fullname,
            request.route_url("person", id=user.user_id),
            user.user.fullname,
            (
                translate(_('Attended'))
                if user.status == AttendanceStatus.ATTENDED
                else translate(_('Invited'))
            ),
            user.user_id,
            'checked' if user.status == AttendanceStatus.ATTENDED else '',
            user.user_id,
        )
        for user in sorted(users, key=lambda user: user.user.fullname)
    )
    return Markup(
        '''
    <div class="generic-user-list-container">
        <p>
            <span class="fw-bold">{}</span>
        </p>
        <ul class="generic-user-list list-unstyled multi-col-layout">{}</ul>
    </div>
    '''
    ).format(title, Markup('').join(user_items))


def export_meeting_as_pdf_view(
        context: Meeting, request: 'IRequest',
) -> Response:
    session = request.dbsession
    meeting_id = context.id
    meeting = session.get(Meeting, meeting_id)
    if meeting is None:
        return HTTPNotFound()

    renderer = HTMLReportRenderer()
    options = ReportOptions(language=request.locale_name)
    report = MeetingReport(request, meeting, options, renderer).build()

    response = Response(report.data)
    response.content_type = 'application/pdf'
    name = translate(_('Meeting Report'))
    safe_filename = name + '.pdf'
    response.content_disposition = f'attachment; filename="{safe_filename}"'
    log.info(f'Content-Disposition: {response.content_disposition}')
    return response


def export_meeting_as_docx_view(
        context: Meeting, request: 'IRequest',
) -> Response:
    """Exports the meeting report as a Word (.docx) file."""
    session = request.dbsession
    meeting_id = context.id
    # Use eager loading for related objects if performance becomes an issue
    meeting = session.get(Meeting, meeting_id)
    if meeting is None:
        return HTTPNotFound()

    renderer = WordReportRenderer()
    options = ReportOptions(language=request.locale_name)
    # Pass the specific renderer instance
    report_builder = MeetingReport(request, meeting, options, renderer)
    report_doc = report_builder.build()  # build() now uses the passed renderer

    response = Response(report_doc.data)
    response.content_type = ('application/vnd.openxmlformats-officedocument'
                             '.wordprocessingml.document')
    safe_filename = report_doc.filename
    response.content_disposition = f'attachment; filename="{safe_filename}"'
    log.info(f'Content-Disposition: {response.content_disposition}')
    return response


def working_group_view(
    context: WorkingGroup, request: 'IRequest'
) -> 'RenderData':
    """Displays the table of meetings a single working group has."""

    assert isinstance(context, WorkingGroup)
    request.add_action_menu_entries(
        (
            Button(
                url=request.route_url('edit_working_group', id=context.id),
                icon='edit',
                title=_('Edit'),
                description=_('Edit Working Group'),
                css_class='dropdown-item',
            ),
            Button(
                url=request.route_url('delete_working_group', id=context.id),
                icon='trash',
                title=_('Delete'),
                description=_('Delete Working Group'),
                css_class='dropdown-item',
                modal='#delete-xhr',
                data_item_title=context.name,
            ),
        )
    )

    chairman = context.chairman
    base_dict = {
        'title': context.name,
        'users': [
            {
                'profile_pic': user.profile_pic_download_link(request),
                'fullname': user.fullname,
                'url': request.route_url("person", id=user.id),
            } for user in sorted(context.users, key=lambda user: user.fullname)
        ],
        'participants': translate(_('Participants')),
        'delete_title': _('Delete Working Group'),
        'leader': context.leader or '',
        'leader_link': request.route_url('person', id=context.leader_id),
        'chairman': chairman,
        'add_meeting_link': request.route_url('add_meeting', id=context.id),
        'navigate_back_up': request.route_url('working_groups'),
        'meetings': context.meetings,
        'request': request
    }

    chairman_dict = {}
    if chairman is not None:
        chairman_dict = {
            'chairman_profile': chairman.profile_pic_download_link(request),
            'chairman_fullname': chairman.fullname,
            'chairman_link': request.route_url('person', id=chairman.id),
        }
    return {**base_dict, **chairman_dict}


def add_meeting_view(
        context: WorkingGroup,
        request: 'IRequest'
) -> 'MixedDataOrRedirect':

    assert isinstance(context, WorkingGroup)
    form = MeetingForm(context, request)
    session = request.dbsession

    target_url = request.route_url('meetings', id=context.id)
    if request.method == 'POST' and form.validate():
        assert form.name.data
        assert form.time.data
        time = fix_utc_to_local_time(form.time.data)

        meeting = Meeting(
            name=form.name.data,
            time=time,
            attendees=[],  # sync_meeting_attendance_records will handle this
            working_group=context,
            creator=request.user
        )

        # XXX A pragmatic shortcut that holds up, for the time being.
        #
        # In the frontend, we are displaying just attendees, it looks like a
        # list uf users, but it's actually stored in `MeetingUserAttendance`.
        # This creates a sort of inconsistency, which is why the lines below
        # are necessary.
        form_attendees = set(form.attendees.data or [])
        working_group_attendees = {str(user.id) for user in context.users}
        # As per requirements, the users of the working group always attend the
        # meeting by default.
        form.attendees.data = list(form_attendees | working_group_attendees)
        sync_meeting_attendance_records(form, meeting, request.POST, session)

        added_filenames = []
        if form.files.data:
            for file in form.files.data:
                if file:
                    # Explicitly set meeting_id, consultation_id defaults
                    # to None
                    searchable_file = SearchableFile(
                        filename=file['filename'],
                        content=dictionary_to_binary(file),
                        content_type=file['mimetype'],
                    )
                    # Appending to the relationship automatically handles the
                    # foreign key (meeting_id) upon session flush.
                    meeting.files.append(searchable_file)
                    added_filenames.append(file['filename'])

        session.add(meeting)
        session.flush()
        activity = MeetingEditEvent(
            meeting_id=meeting.id,
            event_type='creation',
            creator_id=request.user.id,
            added_files=added_filenames if added_filenames else None
        )
        session.add(activity)
        message = _(
            'Successfully added meeting "${name}"',
            mapping={'name': form.name.data}
        )
        request.messages.add(message, 'success')
        return HTTPFound(
            location=request.route_url('meeting', id=meeting.id),
        )

    if request.is_xhr:
        return {'errors': form.errors}
    else:
        return {
            'form': form,
            'title': form._title,
            'target_url': target_url,
            'csrf_token': request.session.get_csrf_token()
        }


def edit_meeting_view(
    meeting: Meeting, request: 'IRequest'
) -> 'MixedDataOrRedirect':

    assert isinstance(meeting, Meeting)

    target_url = request.route_url('meeting', id=meeting.id)
    form = MeetingForm(meeting, request)
    session = request.dbsession

    if request.method == 'POST' and form.validate():
        # Store original data for comparison
        original_data = {
            'name': meeting.name,
            'time': meeting.time,
            'attendance': {
                record.user_id: record.status
                for record in meeting.attendance_records
            }
        }
        assert form.time.data is not None

        # Determine removed files before populating the object
        removed_files = [
            entry.object_data for entry in form.files.entries
            if entry.action in ('delete', 'replace') and entry.object_data
        ]
        removed_filenames = [f.filename for f in removed_files]

        form.populate_obj(meeting)
        meeting.time = fix_utc_to_local_time(form.time.data)

        # Track changes
        changes = meeting.track_changes(original_data)

        # form.files.added_files is populated by populate_obj
        added_filenames = [
            f.filename for f in getattr(form.files, 'added_files', [])
        ]
        files_were_added = bool(added_filenames)
        files_were_removed = bool(removed_filenames)
        file_changes = files_were_added or files_were_removed

        if changes and file_changes:
            activity = MeetingEditEvent(
                meeting_id=meeting.id,
                event_type='update',
                creator_id=request.user.id,
                changes=changes,
                added_files=added_filenames if added_filenames else None,
                removed_files=removed_filenames if removed_filenames else None,
            )
            session.add(activity)

        if file_changes and not changes:
            # 'pure' file update
            activity = MeetingEditEvent(
                meeting_id=meeting.id,
                event_type='file_update',
                creator_id=request.user.id,
                added_files=added_filenames if added_filenames else None,
                removed_files=removed_filenames if removed_filenames else None,
            )
            session.add(activity)

        session.add(meeting)
        session.flush()
        message = _('Successfully edited meeting.')
        if not request.is_xhr:
            request.messages.add(message, 'success')
        return HTTPFound(location=request.route_url('meeting', id=meeting.id))

    return {
        'form': form,
        'target_url': target_url,
        'title': form._title,
    }


def delete_meeting_view(
        context: Meeting,
        request: 'IRequest'
) -> 'XHRDataOrRedirect':

    assert isinstance(context, Meeting)
    name = context.name
    working_group_id = context.working_group.id

    session = request.dbsession
    session.delete(context)
    session.flush()

    message = _(
        'Successfully deleted meeting "${name}"',
        mapping={'name': name}
    )

    request.messages.add(message, 'success')
    if request.is_xhr:
        return {
            'success': translate(message, request.locale_name),
            'redirect_url': request.route_url('meetings', id=working_group_id),
        }

    return HTTPFound(
        location=request.route_url('meetings', id=working_group_id),
    )


def move_agenda_item(context: Meeting, request: 'IRequest') -> 'RenderData':
    try:
        subject_id = int(request.matchdict['subject_id'])
        direction = request.matchdict['direction']
        target_id = int(request.matchdict['target_id'])
    except (ValueError, KeyError) as e:
        raise HTTPBadRequest('Request parameters are missing or invalid') \
            from e

    if direction not in ['above', 'below']:
        raise HTTPMethodNotAllowed('Invalid direction')

    # Get all agenda items sorted by position
    items = context.agenda_items

    # Find the items we're working with
    subject_item = next(
        (item for item in items if item.position == subject_id), None
    )
    target_item = next(
        (item for item in items if item.position == target_id), None
    )

    if not subject_item or not target_item:
        raise HTTPMethodNotAllowed('Invalid subject or target id')

    old_pos = subject_item.position
    new_pos = (
        target_item.position if direction == 'above'
        else target_item.position + 1
    )

    # Adjust positions of items between old and new positions
    for item in items:
        if old_pos < new_pos:
            # Moving down
            if old_pos < item.position <= new_pos - 1:
                item.position -= 1
        else:
            # Moving up
            if new_pos <= item.position < old_pos:
                item.position += 1

    # Set the subject item's new position
    subject_item.position = new_pos - 1 if old_pos < new_pos else new_pos

    return {
        'status': 'success',
        'subject_id': subject_id,
        'direction': direction,
        'target_id': target_id,
    }
