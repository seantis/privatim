from typing import overload
from typing import Any
from typing import TypeVar
from zope.interface.interfaces import IInterface
from zope.interface.registry import Components

from pyramid.path import _CALLER_PACKAGE

_T = TypeVar('_T')
_I = TypeVar('_I', bound=IInterface)

# NOTE: Technically Registry also derives from dict, but we never
#       use it like that, so for simplicity, let's not inherit
class Registry(Components):
    settings: dict[str, Any]
    package_name: str
    def __init__(self, package_name: str | _CALLER_PACKAGE = ..., *args: Any, **kw: Any) -> None: ...
    def notify(self, *events: Any) -> None: ...
    def registerSelfAdapter(
        self,
        required: Any | None = ...,
        provided: Any | None = ...,
        name: str = ...,
        info: str = ...,
        event: bool = ...
    ) -> None: ...
    @overload
    def queryAdapterOrSelf(
        self,
        object: Any,
        interface: type[_I],
        default: None = None
    ) -> _I | None: ...
    @overload
    def queryAdapterOrSelf(
        self,
        object: Any,
        interface: type[_I],
        default: _T
    ) -> _I | _T: ...
