from typing import overload
from typing import Any
from typing import TypeVar
from zope.interface import Interface
from zope.interface.registry import Components

_T = TypeVar('_T')
_I = TypeVar('_I', bound=Interface)


# NOTE: Technically Registry also derives from dict, but we never
#       use it like that, so for simplicity, let's not inherit
class Registry(Components):
    settings: dict[str, Any]
    package_name: str
    def __init__(self, package_name: str = ..., *args: Any, **kw: Any) -> None: ...
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
    ) -> _I | None: ...
    @overload
    def queryAdapterOrSelf(
        self,
        object: Any,
        interface: type[_I],
        default: _T = ...
    ) -> _I | _T: ...
    @overload
    def queryAdapterOrSelf(
        self,
        object: Any,
        interface: type[_T],
        default: _I = ...
    ) -> _I: ...
    # NOTE: We overwrite some of the stubs from Component, because
    #       they are not as smart about the default parameter
    @overload  # type:ignore[override]
    def queryUtility(
        self,
        provided: type[_I],
        name: str = ...,
    ) -> _I | None: ...
    @overload
    def queryUtility(
        self,
        provided: type[_I],
        name: str = ...,
        default: _T = ...
    ) -> _I | _T: ...
    @overload
    def queryUtility(
        self,
        provided: type[_T],
        name: str = ...,
        default: _I = ...
    ) -> _I: ...
    @overload  # type:ignore[override]
    def queryAdapter(
        self,
        object: Any,
        interface: type[_I],
        name: str = ...,
    ) -> _I | None: ...
    @overload
    def queryAdapter(
        self,
        object: Any,
        interface: type[_I],
        name: str = ...,
        default: _T = ...
    ) -> _I | _T: ...
    @overload
    def queryAdapter(
        self,
        object: Any,
        interface: type[_T],
        name: str = ...,
        default: _I = ...
    ) -> _I: ...

    @overload  # type:ignore[override]
    def queryMultiAdapter(
        self,
        objects: Any,
        interface: type[_I],
        name: str = ...,
    ) -> _I | None: ...
    @overload
    def queryMultiAdapter(
        self,
        objects: Any,
        interface: type[_I],
        name: str = ...,
        default: _T = ...
    ) -> _I | _T: ...
    @overload
    def queryMultiAdapter(
        self,
        objects: Any,
        interface: type[_T],
        name: str = ...,
        default: _I = ...
    ) -> _I: ...
