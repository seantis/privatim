from typing import Any
from typing import TypeVar

from pyramid.config import Configurator
from pyramid.interfaces import IPredicate
from pyramid.interfaces import IPredicateFactory


_T = TypeVar('_T')

class PredicateList:
    def __init__(self) -> None: ...
    def add(
        self,
        name: str,
        factory: IPredicateFactory | str,
        weighs_more_than: str | None = ...,
        weighs_less_than: str | None = ...
    ) -> None: ...
    def names(self) -> list[str]: ...
    def make(
        self,
        config: Configurator,
        **kwargs: Any
    ) -> tuple[int, list[IPredicate], str]: ...

class PredicateConfiguratorMixin:
    def get_predlist(self, name: str) -> PredicateList: ...

# NOTE: Technicall not_ is a class and should only be used on
#       predicate parameters, but for convenience we treat it
#       as a function that returns the same type as we put in
#       so we can use not_ without having to explicitly allow
#       it for each predicate argument
def not_(value: _T) -> _T: ...
