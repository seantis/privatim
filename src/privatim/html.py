
from bleach.sanitizer import Cleaner  # type:ignore[import-untyped]
from markupsafe import Markup


from typing import TypeVar


_StrT = TypeVar('_StrT', bound=str)


# html tags allowed by bleach
SANE_HTML_TAGS = [
    'a',
    'abbr',
    'b',
    'br',
    'blockquote',
    'code',
    'del',
    'div',
    'em',
    'i',
    'img',
    'hr',
    'li',
    'ol',
    'p',
    'pre',
    'strong',
    'sup',
    'span',
    'ul',
    'h1',
    'h2',
    'h3',
    'h4',
    'h5',
    'h6',
    'table',
    'tbody',
    'thead',
    'tr',
    'th',
    'td',
]

# html attributes allowed by bleach
SANE_HTML_ATTRS = {
    'a': ['href', 'title'],
    'abbr': ['title', ],
    'acronym': ['title', ],
    'img': ['src', 'alt', 'title']
}


cleaner = Cleaner(
    tags=SANE_HTML_TAGS,
    attributes=SANE_HTML_ATTRS
)


def sanitize_html(html: str | None) -> Markup:
    """ Takes the given html and strips all but a whitelisted number of tags
    from it.

    """

    return Markup(cleaner.clean(html or ''))
