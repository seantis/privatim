from typing import Any, TypeVar

from pyramid.interfaces import IRequest
from zope.interface import Interface

_T = TypeVar("_T")

class LayoutManager:
    context: Any
    request: IRequest
    layout: Any
    def __init__(self, context: Any, request: IRequest) -> None: ...
    def use_layout(self, name: str) -> None: ...
    def render_panel(self, name: str = "", *args: Any, **kw: Any) -> Structure: ...

def find_layout(context: Any, request: IRequest, name: str = "") -> Any: ...

class Structure(str):
    def __html__(self) -> str: ...

class layout_config:
    name: str
    context: type | Interface | str | None
    template: str | None
    containment: type | Interface | str | None
    def __init__(
        self,
        name: str = "",
        context: type | Interface | str | None = None,
        template: str | None = None,
        containment: type | Interface | str | None = None,
    ) -> None: ...
    def __call__(self, wrapped: _T) -> _T: ...
