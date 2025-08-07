from _typeshed import SupportsItems
from collections.abc import Sequence
from typing import Any, Final, Literal

__all__ = ["InconsistentResolutionOrderError", "InconsistentResolutionOrderWarning", "ro"]

class InconsistentResolutionOrderWarning(PendingDeprecationWarning): ...

class InconsistentResolutionOrderError(TypeError):
    C: C3
    base_ros: dict[type[object], list[type[object]]]
    base_tree_remaining: list[list[type[object]]]
    def __init__(self, c3: C3, base_tree_remaining: list[list[type[object]]]) -> None: ...

class _StaticMRO:
    had_inconsistency: None
    leaf: type[object]
    def __init__(self, C: type[object], mro: Sequence[type[object]]) -> None: ...
    def mro(self) -> list[type[object]]: ...

class C3:
    @staticmethod
    def resolver(C: type[object], strict: bool | None, base_mros: SupportsItems[type[object], list[type[object]]] | None) -> C3: ...
    direct_inconsistency: bool
    leaf: type[object]
    memo: dict[type[object], _StaticMRO]
    base_tree: list[list[type[object]]]
    bases_had_inconsistency: bool
    def __init__(self, C: type[object], memo: dict[type[object], _StaticMRO]) -> None: ...
    @property
    def had_inconsistency(self) -> bool: ...
    @property
    def legacy_ro(self) -> list[type[object]]: ...
    TRACK_BAD_IRO: Final[Literal[0, 1]]
    STRICT_IRO: Final[Literal[0, 1]]
    WARN_BAD_IRO: Final[Literal[0, 1]]
    LOG_CHANGED_IRO: Final[Literal[0, 1]]
    USE_LEGACY_IRO: Final[Literal[0, 1]]
    ORIG_TRACK_BAD_IRO: Final[Literal[0, 1]]
    ORIG_STRICT_IRO: Final[Literal[0, 1]]
    ORIG_WARN_BAD_IRO: Final[Literal[0, 1]]
    ORIG_LOG_CHANGED_IRO: Final[Literal[0, 1]]
    ORIG_USE_LEGACY_IRO: Final[Literal[0, 1]]
    # TODO: Should probably be a WeakKeyDictionary
    BAD_IROS: Final[Any]
    def mro(self) -> list[type[object]]: ...

def ro(C: type[object], strict: bool | None = None, base_mros: SupportsItems[type[object], Sequence[type[object]]] | None = None, log_changed_ro: bool | None = None, use_legacy_ro: bool | None = None) -> list[type[object]]: ...
