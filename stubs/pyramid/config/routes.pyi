from collections.abc import Callable
from collections.abc import Iterable
from collections.abc import Iterator
from collections.abc import Sequence
from contextlib import contextmanager
from typing import Any
from typing import Protocol
from webob.request import _HTTPMethod

from pyramid.interfaces import IPredicateFactory
from pyramid.interfaces import IPredicateInfo
from pyramid.interfaces import IRequest
from pyramid.interfaces import IRootFactory
from pyramid.interfaces import IRoutePregenerator
from pyramid.interfaces import IRoutesMapper


class _RoutePredicateClass(Protocol):
    def __init__(self, __value: Any, __info: IPredicateInfo, /): ...
    def text(self) -> str: ...
    def phash(self) -> str: ...
    def __call__(self, request: IRequest) -> bool: ...

class RoutesConfiguratorMixin:
    def add_route(
        self,
        name: str,
        pattern: str | None = ...,
        factory: IRootFactory | Callable[[IRequest], Any] | str | None = ...,
        for_: None = ...,  # deprecated
        header: str | Iterable[str] | None = ...,
        xhr: bool | None = ...,
        accept: str | list[str] | None = ...,
        path_info: str | None = ...,
        request_method: _HTTPMethod | tuple[_HTTPMethod, ...] | None = ...,
        request_param: str | Iterable[str] | None = ...,
        traverse: str | None = ...,
        custom_predicates: Sequence[Any] = ...,  # deprecated
        use_global_views: bool = ...,
        path: str | None = ...,
        pregenerator: IRoutePregenerator | str | None = ...,
        static: bool = ...,
        inherit_slash: bool | None = ...,
        *,
        is_authenticated: bool = ...,
        effective_principals: str | Sequence[str] = ...,
        # NOTE: if we had any custom route predicated defined
        #       we would add them here in order to type check them
        **predicates: Any
    ): ...
    def add_route_predicate(
        self,
        name: str,
        factory: IPredicateFactory | type[_RoutePredicateClass] | str,
        weighs_more_than: str | None = ...,
        weighs_less_than: str | None = ...
    ) -> None: ...
    def get_routes_mapper(self) -> IRoutesMapper: ...
    @contextmanager
    def route_prefix_context(self, route_prefix: str) -> Iterator[None]: ...
