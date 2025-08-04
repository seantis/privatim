from typing import Any

from markupsafe import HasHTML
from pyramid.interfaces import IRequest
from zope.interface import Interface

class ILayoutManager(Interface):
    # NOTE: These are not technically part of the interface, but the
    #       interface is useless without these attributes
    layout: Any
    def use_layout(name: str) -> None: ...
    def render_panel(name: str = "", *args: Any, **kw: Any) -> HasHTML: ...

class ILayout(Interface): ...

class IPanel(Interface):
    def __call__(context: Any, request: IRequest, *args: Any, **kw: Any) -> None: ...
