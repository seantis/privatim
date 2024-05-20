from privatim.static import bootstrap_css, bootstrap_js, tom_select_css
from pytz import timezone
import re
from datetime import date, datetime


from typing import Any, TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from pytz import BaseTzInfo


DEFAULT_TIMEZONE = timezone('Europe/Zurich')

_private_regex = re.compile(r':[0-9a-z]+@')


class Layout:

    def __init__(self, context: Any, request: 'IRequest') -> None:
        self.context = context
        self.request = request
        self.year = date.today().year

        bootstrap_css.need()
        bootstrap_js.need()
        tom_select_css.need()

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

    def datetime_format(
            self,
            dt: datetime,
            format: str = '%H:%M %d.%m.%y',
            tz: 'BaseTzInfo' = DEFAULT_TIMEZONE
    ) -> str:

        if not dt.tzinfo:
            # If passed datetime does not carry any timezone information, we
            # assume (and force) it to be UTC, as all timestamps should be.
            dt = timezone('UTC').localize(dt)

        return dt.astimezone(tz).strftime(format)
