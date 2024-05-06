from collections.abc import Callable
from typing import Any
from typing import Protocol
from zope.interface import Interface

from pyramid.interfaces import IPredicateFactory
from pyramid.interfaces import IPredicateInfo


class _SubscriberPredicateClass(Protocol):
    def __init__(self, __value: Any, __info: IPredicateInfo, /): ...
    def text(self) -> str: ...
    def phash(self) -> str: ...
    def __call__(self, event: Any) -> bool: ...


class AdaptersConfiguratorMixin:
    def add_subscriber(
        self,
        subscriber: Callable[[Any], Any] | str,
        iface: Interface | type | str | None = ...,
        # NOTE: if we had any custom subcriber predicates defined
        #       we would add them here in order to type check them
        **predicates: Any
    ) -> Callable[[Any], None]: ...
    def add_subscriber_predicate(
        self,
        name: str,
        factory: IPredicateFactory | type[_SubscriberPredicateClass] | str,
        weighs_more_than: str | None = ...,
        weighs_less_than: str | None = ...
    ) -> None: ...
    def add_response_adapter(
        self,
        adapter: Callable[[Any], Any] | None,
        type_or_iface: Interface | type | str
    ) -> None: ...
