import base64
import gzip
from functools import lru_cache
from PIL import Image
import magic
from io import BytesIO

from pytz import timezone, BaseTzInfo
from sedate import to_timezone
from markupsafe import escape

from privatim.layouts.layout import DEFAULT_TIMEZONE


from typing import Any, TYPE_CHECKING, overload
if TYPE_CHECKING:
    from privatim.types import FileDict, LaxFileDict
    from typing import Iterable
    from datetime import datetime
    from privatim.models.commentable import Comment
    from pyramid.interfaces import IRequest
    from typing import TypedDict

    class ChildCommentDict(TypedDict):
        comment: 'Comment'
        picture: str

    class FlattenedCommentDict(TypedDict):
        comment: 'Comment'
        children: list['ChildCommentDict']
        picture: str


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


@lru_cache(maxsize=1)
def get_supported_image_mime_types() -> set[str]:
    """ Queries PIL for *all* locally supported mime types.

    Adapted from:
    https://github.com/python-pillow/Pillow/issues/1182#issuecomment-90572583

    """

    # Make sure all supported formats are registered.
    Image.init()

    # Not all PIL formats register a mime type, fill in the blanks ourselves.
    supported_types = {
        'image/bmp',
        'image/x-bmp',
        'image/x-MS-bmp',
        'image/x-icon',
        'image/x-ico',
        'image/x-win-bitmap',
        'image/x-pcx',
        'image/x-portable-pixmap',
        'image/x-tga'
    }

    for mime in Image.MIME.values():

        # exclude pdfs, postscripts and the like
        if not mime.startswith('application/'):
            supported_types.add(mime)

    return supported_types


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


def flatten_comments(
    top_level_comments: 'Iterable[Comment]',
    fallback_profile_pic: str,
    request: 'IRequest',
) -> list['FlattenedCommentDict']:
    """
    Comments naturally contain arbitrary levels of nesting. (Each reply is a
    child.) This basically returns a list of comments with level of depth=1.

    The UI only shows one level of nesting, so deeply nested comments
    are not displayed with further indentation. Which is why this function
    does not need to do a full-blown tree traversal."""

    flattened_comments: list['FlattenedCommentDict'] = []
    for comment in top_level_comments:
        children = sorted(comment.children, key=lambda c: c.created)
        pic = handle_comment_picture(comment, fallback_profile_pic, request)

        # Process children comments
        _children: list['ChildCommentDict'] = []
        for child in children:
            child_pic = handle_comment_picture(
                child, fallback_profile_pic, request
            )
            _children.append({'comment': child, 'picture': child_pic})

        flattened_comments.append(
            {'comment': comment, 'children': _children, 'picture': pic}
        )
    return flattened_comments


def handle_comment_picture(
    comment: 'Comment', fallback_profile_pic_link: str, request: 'IRequest'
) -> str:
    if comment.user is None:
        pic = fallback_profile_pic_link
    else:
        if comment.user.id == request.user.id:
            pic = request.profile_pic
        else:
            pic = (
                request.route_url(
                    'download_general_file', id=comment.user.profile_pic.id
                )
                if comment.user.profile_pic is not None
                else fallback_profile_pic_link
            )
    return pic


def maybe_escape(value: str | None) -> str:
    if value is None:
        return ''
    return escape(value)
