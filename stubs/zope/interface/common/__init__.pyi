from abc import ABCMeta
from collections.abc import Callable
from typing import Any

from zope.interface.interface import InterfaceClass

__all__: list[str] = []

# NOTE: We could try to support these through the plugin, but it seems
#       more reliably and easier to just mirror the interface for now
# FIXME: For some reason the mypy plugin causes ABCInterface to turn into Any
#        so before we can even think about supporting ABCInterfaceClass
#        we would have to fix that
class optional:
    __doc__: str | None
    def __init__(self, method: Callable[..., Any]) -> None: ...

class ABCInterfaceClass(InterfaceClass):
    def getABC(self) -> ABCMeta: ...
    def getRegisteredConformers(self) -> set[type[object]]: ...

class ABCInterface(metaclass=ABCInterfaceClass): ...
