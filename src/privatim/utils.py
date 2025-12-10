from __future__ import annotations
import base64
import gzip
import magic
from io import BytesIO

from pytz import timezone, BaseTzInfo
from sedate import to_timezone
from markupsafe import escape
from sqlalchemy import select, text
from sqlalchemy.orm import DeclarativeBase, joinedload, load_only

from privatim.models import Consultation, Meeting
from privatim.models import User, WorkingGroup
from privatim.layouts.layout import DEFAULT_TIMEZONE


from typing import Any, TYPE_CHECKING, overload, TypeVar
if TYPE_CHECKING:
    from privatim import UpgradeContext
    from collections.abc import Mapping
    from privatim.types import FileDict, LaxFileDict
    from collections.abc import Iterable
    from datetime import datetime
    from privatim.orm import FilteredSession

    T = TypeVar('T', bound=DeclarativeBase)


def datetime_format(
        dt: datetime,
        format: str = '%d.%m.%y %H:%M',
        tz: BaseTzInfo = DEFAULT_TIMEZONE
) -> str:

    if not dt.tzinfo:
        # If passed datetime does not carry any timezone information, we
        # assume (and force) it to be UTC, as all timestamps should be.
        dt = timezone('UTC').localize(dt)
    return dt.astimezone(tz).strftime(format)


def first(iterable: Iterable[Any] | None, default: Any | None = None) -> Any:
    """
    Returns first item in given iterable or a default value.
    """
    return next(iter(iterable), default) if iterable else default


def binary_to_dictionary(
    binary: bytes, filename: str | None = None
) -> FileDict:
    """Takes raw binary filedata and stores it in a dictionary together
    with metadata information.

    The data is compressed before it is stored int he dictionary. Use
    :func:`dictionary_to_binary` to get the original binary data back.

    """

    assert isinstance(binary, bytes)

    mimetype = magic.from_buffer(binary, mime=True)

    # according to https://tools.ietf.org/html/rfc7111, text/csv should be used
    if mimetype == 'application/csv':
        mimetype = 'text/csv'

    gzipdata = BytesIO()

    with gzip.GzipFile(fileobj=gzipdata, mode='wb') as f:
        f.write(binary)

    return {
        'data': base64.b64encode(gzipdata.getvalue()).decode('ascii'),
        'filename': filename,
        'mimetype': mimetype,
        'size': len(binary),
    }


def dictionary_to_binary(dictionary: LaxFileDict) -> bytes:
    """Takes a dictionary created by :func:`binary_to_dictionary` and returns
    the original binary data.

    """
    data = base64.b64decode(dictionary['data'])

    with gzip.GzipFile(fileobj=BytesIO(data), mode='r') as f:
        return f.read()


@overload
def path_to_filename(path: None) -> None: ...
@overload
def path_to_filename(path: str) -> str: ...


def path_to_filename(path: str | None) -> str | None:
    if not path:
        return None
    if not isinstance(path, str):
        raise ValueError
    if '/' in path:
        return path.rsplit('/', 1)[-1]
    if '\\' in path:
        return path.rsplit('\\', 1)[-1]
    return path


def fix_utc_to_local_time(db_time: datetime) -> datetime:
    return (db_time and to_timezone(
        db_time, 'Europe/Zurich')) or db_time


def maybe_escape(value: str | None) -> str:
    if value is None:
        return ''
    return escape(value)


def strip_p_tags(text: str) -> str:
    """Remove <p> tags and strip whitespace from the given text.

    Typically used to display HTML within <ul> and <li> tags, where <p> tags
    would break the layout. It's not the most elegant solution, but less likely
    to break in the future than other approaches.
    """
    _text = text.replace('<p>', '').replace('</p>', '')
    return _text.strip()


def status_is_checked(data: Mapping[str, Any], user_id: str) -> bool:
    """ Returns true if for the given user the checkbox has been checked,
    false otherwise. """
    # Find the index for the given user_id
    user_indices = [
        int(key.split('-')[1])
        for key, value in data.items()
        if key.endswith('-user_id') and value == user_id
    ]

    if not user_indices:
        return False  # User ID not found

    # Check if there's a corresponding status for this index and if it's 'y'
    for index in user_indices:
        status_key = f'attendance-{index}-status'
        if status_key in data and data[status_key] == 'y':
            return True

    return False


def get_previous_versions(
    session: FilteredSession, consultation: Consultation, limit: int = 5
) -> list[Consultation]:
    """
    Returns the previous versions of a consultation.

    This function is more complex than it should be, unfortunately. It seems
    necessary, though. Take a quick glance at the unused function
    simple_get_previous_versions (found below); it looks reasonable.

    However, it doesn't work in some cases.
    Consultation.previous_version would return None — it really wasn't.
    Thus, we need to resort to low-level stuff.
    """

    with session.no_consultation_filter():
        query = text(
            """
        WITH RECURSIVE versions AS (
            SELECT id, replaced_consultation_id
            FROM consultations
            WHERE id = :id
            UNION ALL
            SELECT c.id, c.replaced_consultation_id
            FROM consultations c
            JOIN versions v ON c.replaced_consultation_id = v.id
        )
        SELECT id FROM versions
        WHERE id != :id AND replaced_consultation_id IS NOT NULL
        LIMIT :limit
        """
        )
        version_ids = (
            session.execute(query, {'id': consultation.id, 'limit': limit})
            .scalars()
            .all()
        )
        try:
            return list(
                session.execute(
                    select(Consultation)
                    .where(Consultation.id.in_(version_ids))
                    .options(joinedload(Consultation.creator))
                    .order_by(Consultation.created.desc())
                )
                .scalars()
                .all()
            )
        except Exception:
            return []


class ConsultationVersion:
    def __init__(self, created: datetime, editor: User | None, title: str):
        self.created = created
        self.editor = editor
        self.title = title

    def __repr__(self) -> str:
        editor_repr = (
            f"User(id='{self.editor.id}', email='{self.editor.email}')"
            if self.editor
            else None
        )
        return (
            f"ConsultationVersion(created={self.created}, "
            f"editor={editor_repr}, title='{self.title}')"
        )


def simple_get_previous_versions(
    session: FilteredSession,
    latest_consultation_id: str,
    limit: int | None = 5,
) -> list[ConsultationVersion]:
    """Not used currently."""
    with session.no_consultation_filter():
        # Fetch the latest version of the consultation

        # TODO: Be cautious - filtered sessions have unexpected behavior here
        #       Loading previous consultation versions likely requires
        #       selectinload() Replace current implementation with this
        #       approach instead of the complex `get_previous_versions`

        #
        # latest_cons = session.execute(
        #     select(Consultation)
        #     .options(
        #         selectinload(Consultation.previous_version).selectinload(
        #             Consultation.previous_version
        #         )
        #     )
        #     .filter_by(description='second update description')
        # ).scalar_one()

        latest_consultation = session.get(Consultation, latest_consultation_id)

        if not latest_consultation:
            return []

        versions = []
        current_version = (
            latest_consultation.previous_version
        )  # Skip the latest version
        count = 0
        while current_version and (limit is None or count < limit):
            versions.append(
                ConsultationVersion(
                    created=current_version.created,
                    editor=current_version.editor,
                    title=current_version.title,
                )
            )
            current_version = current_version.previous_version
            count += 1
        return versions


def get_guest_and_removed_users(
    session: FilteredSession, context: Meeting | WorkingGroup
) -> tuple[set[User], set[User]]:
    # Get ALL users first
    all_users_query = (
        select(User)
        .options(load_only(User.id, User.first_name, User.last_name))
        .order_by(User.first_name, User.last_name)
    )
    all_users = session.execute(all_users_query).scalars().all()

    guest_users: set[User] = set()
    removed_users: set[User] = set()

    if isinstance(context, Meeting):
        working_group_members_ids = {
            str(user.id) for user in context.working_group.users
        }
        # Ensure we only consider valid, existing user IDs from records
        valid_user_ids_in_db = {str(u.id) for u in all_users}
        existing_attendee_ids = {
            str(record.user_id) for record in context.attendance_records
            if record.user_id and str(record.user_id) in valid_user_ids_in_db
        }

        for user in all_users:
            user_id_str = str(user.id)
            is_wg_member = user_id_str in working_group_members_ids
            is_current_attendee = user_id_str in existing_attendee_ids

            if is_wg_member:
                if not is_current_attendee:
                    # This is a WG member who is not currently an attendee
                    # (e.g., was removed or never initially added).
                    # They should be available to be (re-)added.
                    removed_users.add(user)
                # If is_wg_member and is_current_attendee, they are already
                # in the meeting, so they don't need to be in the addable list.
            else:  # User is NOT a WG member
                if not is_current_attendee:
                    # This is a non-WG member not currently attending.
                    # They are a potential guest.
                    guest_users.add(user)
                # If not is_wg_member and is_current_attendee, they are
                # a guest already in the meeting. They don't need to be
                # in the addable list.
    else:
        # For a new meeting (context is WorkingGroup),
        # all non-members are potential guests.
        working_group_member_ids = {str(user.id) for user in context.users}
        guest_users = {
            user for user in all_users
            if str(user.id) not in working_group_member_ids
        }
        # No "removed_users" when creating a new meeting from a WG context,
        # as all WG members are typically added by default initially.
    return guest_users, removed_users


def fix_agenda_item_positions(context: UpgradeContext) -> None:
    """Fix agenda item positions to be strictly increasing within each meeting.
    """

    session = context.session

    # Get all meetings that have agenda items
    stmt = select(Meeting).join(Meeting.agenda_items)
    meetings = session.execute(stmt).scalars().unique().all()

    for meeting in meetings:
        # Get agenda items ordered by current position
        items = meeting.agenda_items

        # Reassign positions sequentially
        for new_position, item in enumerate(items):
            item.position = new_position
