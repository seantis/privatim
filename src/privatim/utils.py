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
from privatim.models.profile_pic import get_or_create_default_profile_pic
from privatim.layouts.layout import DEFAULT_TIMEZONE


from typing import Any, TYPE_CHECKING, overload, TypeVar, Callable, Sequence
if TYPE_CHECKING:
    from collections.abc import Mapping
    from privatim.types import FileDict, LaxFileDict
    from typing import Iterable
    from datetime import datetime
    from privatim.orm import FilteredSession
    from privatim.models.comment import Comment
    from pyramid.interfaces import IRequest
    from typing import TypedDict

    class ChildCommentDict(TypedDict):
        comment: 'Comment'
        picture: str

    class FlattenedCommentDict(TypedDict):
        comment: 'Comment'
        children: list['ChildCommentDict']
        picture: str

    T = TypeVar('T', bound=DeclarativeBase)


def datetime_format(
        dt: 'datetime',
        format: str = '%d.%m.%y %H:%M',
        tz: BaseTzInfo = DEFAULT_TIMEZONE
) -> str:

    if not dt.tzinfo:
        # If passed datetime does not carry any timezone information, we
        # assume (and force) it to be UTC, as all timestamps should be.
        dt = timezone('UTC').localize(dt)
    return dt.astimezone(tz).strftime(format)


def first(iterable: 'Iterable[Any] | None', default: Any | None = None) -> Any:
    """
    Returns first item in given iterable or a default value.
    """
    return next(iter(iterable), default) if iterable else default


def binary_to_dictionary(
    binary: bytes, filename: str | None = None
) -> 'FileDict':
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


def dictionary_to_binary(dictionary: 'LaxFileDict') -> bytes:
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


def fix_utc_to_local_time(db_time: 'datetime') -> 'datetime':
    return db_time and to_timezone(
        db_time, 'Europe/Zurich') or db_time


def get_correct_comment_picture_for_comment(
        comment: 'Comment', request: 'IRequest'
) -> str:
    """ Returns a downloadable link to the comment's profile pic."""

    fallback_profile_pic_link = request.route_url(
        'download_file', id=get_or_create_default_profile_pic(
            request.dbsession
        ).id
    )

    if comment.user is None:
        pic = fallback_profile_pic_link
    else:
        if comment.user.id == request.user.id:
            pic = request.profile_pic
        else:
            pic = (
                request.route_url(
                    'download_file', id=comment.user.profile_pic.id
                )
                if comment.user.profile_pic is not None
                else fallback_profile_pic_link
            )
    return pic


def flatten_comments(
    top_level_comments: 'Iterable[Comment]',
    request: 'IRequest',
    get_picture_for_comment: Callable[['Comment', 'IRequest'], str] = (
        get_correct_comment_picture_for_comment
    )
) -> list['FlattenedCommentDict']:
    """
    Returns a list of comments where are child comments are on the same level.

    Comments naturally contain arbitrary levels of nesting. They are trees.
    The UI only shows one level of nesting, so deeply nested comments
    are not displayed with further indentation.

    We pass in the `get_picture_for_comment` callable to ease testing.
    """

    def process_comment(comment: 'Comment') -> 'FlattenedCommentDict':
        pic = get_picture_for_comment(comment, request)
        children = []
        for child in sorted(comment.children, key=lambda c: c.created):
            children.extend(process_comment(child)['children'])
            children.append({
                'comment': child,
                'picture': get_picture_for_comment(
                    child,
                    request
                )
            })
        return {
            'comment': comment,
            'children': children,
            'picture': pic
        }

    return [process_comment(comment) for comment in top_level_comments]


def maybe_escape(value: str | None) -> str:
    if value is None:
        return ''
    return escape(value)


def strip_p_tags(text: str) -> str:
    """Remove <p> tags and strip whitespace from the given text.

    Typically used to display HTML within <ul> and <li> tags,
    ensuring elements remain on the same horizontal line. It's not the most
    elegant solution, but less likely to break in the future.
    """
    _text = text.replace('<p>', '').replace('</p>', '')
    return _text.strip()


def attendance_status(data: 'Mapping[str, Any]', user_id: str) -> bool:
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
    session: 'FilteredSession', consultation: Consultation, limit: int = 5
) -> Sequence[Consultation]:
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
            return (
                session.execute(
                    select(Consultation)
                    .where(Consultation.id.in_(version_ids))
                    .options(joinedload(Consultation.creator))
                )
                .scalars()
                .all()
            )
        except Exception:
            return []


class ConsultationVersion:
    def __init__(self, created: 'datetime', editor: User | None, title: str):
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
    session: 'FilteredSession',
    latest_consultation_id: str,
    limit: int | None = 5,
) -> list[ConsultationVersion]:
    """Not used currently."""
    with session.no_consultation_filter():
        # Fetch the latest version of the consultation
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


def get_guest_users(
    session: 'FilteredSession', context: Meeting | WorkingGroup
) -> 'Sequence[User]':

    # Get ALL users first
    all_users = (
        session.execute(
            select(User)
            .options(load_only(User.id, User.first_name, User.last_name))
            .order_by(User.first_name, User.last_name)
        )
        .scalars()
        .all()
    )

    if isinstance(context, Meeting):
        working_group_members = {
            str(user.id) for user in context.working_group.users
        }
        # Also get existing attendees
        existing_attendees = {
            str(record.user_id) for record in context.attendance_records
        }
        excluded_ids = working_group_members | existing_attendees
    else:
        excluded_ids = {str(user.id) for user in context.users}

    return [
        user for user in all_users if str(user.id) not in excluded_ids
    ]
