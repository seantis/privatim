from collections.abc import Callable
from collections.abc import Iterable
from collections.abc import Sequence
from datetime import timedelta
from typing import Any
from typing import Protocol
from typing_extensions import TypeAlias
from webob.request import _HTTPMethod
from zope.interface import Interface

from pyramid.interfaces import ICacheBuster
from pyramid.interfaces import IPredicateFactory
from pyramid.interfaces import IPredicateInfo
from pyramid.interfaces import IRequest
from pyramid.interfaces import IRootFactory
from pyramid.interfaces import IRoutePregenerator
from pyramid.interfaces import IViewMapper

_Expires: TypeAlias = int | timedelta
_HTTPCache: TypeAlias = tuple[_Expires, dict[str, Any]]
_Decorator: TypeAlias = Callable[[Callable[..., Any]], Callable[..., Any]]
_View: TypeAlias = Callable[[Any, IRequest], Any] | Callable[[IRequest], Any]


class _ViewPredicateClass(Protocol):
    def __init__(self, __value: Any, __info: IPredicateInfo, /): ...
    def text(self) -> str: ...
    def phash(self) -> str: ...
    def __call__(self, context: Any, request: IRequest) -> bool: ...

class ViewsConfiguratorMixin:
    def add_view(
        self,
        view: _View | str | None = ...,
        name: str = ...,
        for_: None = None,  # deprecated
        permission: str | None = ...,
        request_type: None = None,  # deprecated
        route_name: str | None = ...,
        request_method: _HTTPMethod | tuple[_HTTPMethod, ...] | None = ...,
        request_param: str | Sequence[str] | None = ...,
        containment: type | Interface | str | None = ...,
        attr: str | None = ...,
        renderer: str | None = ...,
        wrapper: str | None = ...,
        xhr: bool | None = ...,
        accept: str | None = ...,
        header: str | Iterable[str] | None = ...,
        path_info: str | None = ...,
        custom_predicates: Sequence[Any] = ...,  # deprecated
        context: type | Interface | str | None = ...,
        decorator: _Decorator | str | Iterable[_Decorator | str] | None = ...,
        mapper: IViewMapper | str | None = ...,
        http_cache: _Expires | _HTTPCache | None = ...,
        match_param: str | Sequence[str] | None = ...,
        require_csrf: bool | None = ...,
        exception_only: bool = ...,
        *,
        physical_path: str | tuple[str] = ...,
        is_authenticated: bool = ...,
        effective_principals: str | Sequence[str] = ...,
        # NOTE: here we would add any custom view predicates
        **view_options: Any
    ) -> None: ...
    def add_view_predicate(
        self,
        name: str,
        factory: IPredicateFactory | type[_ViewPredicateClass] | str,
        weighs_more_than: str | None = ...,
        weighs_less_than: str | None = ...
    ) -> None: ...
    def add_accept_view_order(
        self,
        value: str,
        weighs_more_than: str | None = ...,
        weighs_less_than: str | None = ...
    ) -> None: ...
    def add_forbidden_view(
        self,
        view: _View | str | None = ...,
        attr: str | None = ...,
        renderer: str | None = ...,
        wrapper: str | None = ...,
        route_name: str | None = ...,
        request_type: None = None,  # deprecated
        request_method: _HTTPMethod | tuple[_HTTPMethod, ...] | None = ...,
        request_param: str | Sequence[str] | None = ...,
        containment: type | Interface | str | None = ...,
        xhr: bool | None = ...,
        accept: str | None = ...,
        header: str | Iterable[str] | None = ...,
        path_info: str | None = ...,
        custom_predicates: Sequence[Any] = ...,  # deprecated
        decorator: _Decorator | str | Iterable[_Decorator | str] | None = ...,
        mapper: IViewMapper | str | None = ...,
        match_param: str | Sequence[str] | None = ...,
        # NOTE: here we would add any custom view predicates
        **view_options
    ) -> None: ...
    set_forbidden_view = add_forbidden_view
    def add_notfound_view(
        self,
        view: _View | str | None = ...,
        attr: str | None = ...,
        renderer: str | None = ...,
        wrapper: str | None = ...,
        route_name: str | None = ...,
        request_type: None = None,  # deprecated
        request_method: _HTTPMethod | tuple[_HTTPMethod, ...] | None = ...,
        request_param: str | Sequence[str] | None = ...,
        containment: type | Interface | str | None = ...,
        xhr: bool | None = ...,
        accept: str | None = ...,
        header: str | Iterable[str] | None = ...,
        path_info: str | None = ...,
        custom_predicates: Sequence[Any] = ...,  # deprecated
        decorator: _Decorator | str | Iterable[_Decorator | str] | None = ...,
        mapper: IViewMapper | str | None = ...,
        match_param: str | Sequence[str] | None = ...,
        append_slash: bool = ...,
        # NOTE: here we would add any custom view predicates
        **view_options
    ): ...
    set_notfound_view = add_notfound_view
    def add_exception_view(
        self,
        view: _View | str | None = ...,
        context: type[Exception] | None = ...,
        *,
        route_name: str | None = ...,
        request_method: _HTTPMethod | tuple[_HTTPMethod, ...] | None = ...,
        request_param: str | Sequence[str] | None = ...,
        renderer: str | None = ...,
        wrapper: str | None = ...,
        xhr: bool | None = ...,
        accept: str | None = ...,
        header: str | Iterable[str] | None = ...,
        path_info: str | None = ...,
        decorator: _Decorator | str | Iterable[_Decorator | str] | None = ...,
        mapper: IViewMapper | str | None = ...,
        http_cache: _Expires | _HTTPCache | None = ...,
        match_param: str | Sequence[str] | None = ...,
        physical_path: str | tuple[str] = ...,
        is_authenticated: bool = ...,
        effective_principals: str | Sequence[str] = ...,
        # NOTE: here we would add any custom view predicates
        **view_options
    ): ...
    def set_view_mapper(self, mapper: IViewMapper | str) -> None: ...
    def add_static_view(
        self,
        name: str,
        path: str,
        *,
        permission: str | None = ...,
        cache_max_age: int = ...,
        content_encodings: list[str] = ...,
        # NOTE: anything below matches add_route
        factory: IRootFactory | Callable[[IRequest], Any] | str = ...,
        header: str | Iterable[str] | None = ...,
        xhr: bool = ...,
        accept: str | list[str] | None = ...,
        path_info: str | None = ...,
        request_method: _HTTPMethod | tuple[_HTTPMethod, ...] = ...,
        request_param: str | Iterable[str] | None = ...,
        traverse: str = ...,
        use_global_views: bool = ...,
        pregenerator: IRoutePregenerator | str = ...,
        static: bool = ...,
        inherit_slash: bool = ...,
        is_authenticated: bool = ...,
        effective_principals: str | Sequence[str] = ...,
        # NOTE: here we would add any custom route predicates
        **predicates: Any
    ) -> None: ...
    def add_cache_buster(
        self,
        path: str,
        cachebust: ICacheBuster,
        explicit: bool = ...
    ) -> None: ...
