import re
from datetime import date
from typing import Any, TYPE_CHECKING

from privatim.static import bootstrap_css, bootstrap_js, tom_select_css

if TYPE_CHECKING:
    from pyramid.interfaces import IRequest


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
