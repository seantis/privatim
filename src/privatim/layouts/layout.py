import arrow
import babel.dates
import babel.numbers
from pyramid.decorator import reify
from pyramid.renderers import get_renderer
from privatim.static import (bootstrap_css, bootstrap_js, tom_select_css,
                             comments_css, profile_css, sortable_custom,
                             custom_js, init_tiptap_editor)
from pytz import timezone
import re
from datetime import date, datetime


from typing import Any, TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest


DEFAULT_TIMEZONE = timezone('Europe/Zurich')
_private_regex = re.compile(r':[0-9a-z]+@')


class Layout:

    time_format = 'HH:mm'
    date_format = 'dd.MM.yyyy'
    datetime_format = 'dd.MM.yyyy HH:mm'

    date_long_format = 'dd. MMMM yyyy'
    datetime_long_format = 'd. MMMM yyyy HH:mm'
    weekday_long_format = 'EEEE'
    weekday_short_format = 'E'
    month_long_format = 'MMMM'

    def __init__(self, context: Any, request: 'IRequest') -> None:
        self.context = context
        self.request = request
        self.year = date.today().year

        init_tiptap_editor.need()
        bootstrap_css.need()
        bootstrap_js.need()
        tom_select_css.need()
        comments_css.need()
        sortable_custom.need()
        custom_js.need()
        profile_css.need()

    def show_steps(self) -> bool:
        return self.request.show_steps

    def locale_name(self) -> str:
        return self.request.locale_name

    def csrf_token(self) -> str:
        return self.request.session.get_csrf_token()

    def static_url(self, name: str) -> str:
        return self.request.static_url(name)

    def route_url(self, name: str, **kwargs: Any) -> str:
        return self.request.route_url(name, **kwargs)

    def setting(self, name: str) -> Any:
        return self.request.registry.settings.get(name)

    def sentry_dsn(self) -> str | None:
        sentry_dsn = self.setting('sentry_dsn')
        if sentry_dsn:
            return _private_regex.sub('@', sentry_dsn)
        return None

    @reify
    def macros(self) -> Any:
        renderer = get_renderer("macros.pt")
        return renderer.implementation().macros

    def format_date(self, dt: datetime | date | None, format: str) -> str:
        """ Takes a datetime and formats it according to local timezone and
        the given format.

        """
        if dt is None:
            return ''

        if getattr(dt, 'tzinfo', None) is not None:
            dt = DEFAULT_TIMEZONE.normalize(
                dt.astimezone(DEFAULT_TIMEZONE)  # type:ignore[attr-defined]
            )

        locale = self.request.locale_name
        assert locale is not None, "Cannot format date without a locale"
        if format == 'relative':
            adt = arrow.get(dt)

            try:
                return adt.humanize(locale=locale)
            except ValueError:
                return adt.humanize(locale=locale.split('_')[0])

        fmt = getattr(self, format + '_format')
        if fmt.startswith('skeleton:'):
            return babel.dates.format_skeleton(
                fmt.replace('skeleton:', ''),
                datetime=dt,
                fuzzy=False,
                locale=locale
            )
        elif hasattr(dt, 'hour'):
            return babel.dates.format_datetime(dt, format=fmt, locale=locale)
        else:
            return babel.dates.format_date(dt, format=fmt, locale=locale)
