from typing import TypeVar

from pyramid.config.views import _View
from zope.interface import Interface

_ViewT = TypeVar("_ViewT", bound=_View)

class panel_config:
    name: str
    context: type | Interface | str | None
    renderer: str | None
    attr: str | None
    def __init__(
        self,
        name: str = "",
        context: type | Interface | str | None = None,
        renderer: str | None = None,
        attr: str | None = None,
    ) -> None: ...
    def __call__(self, wrapped: _ViewT) -> _ViewT: ...
