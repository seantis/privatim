from typing import Any, TYPE_CHECKING
if TYPE_CHECKING:
    from collections.abc import Iterable


def first(iterable: 'Iterable[Any] | None', default: Any | None = None) -> Any:
    """
    Returns first item in given iterable or a default value.
    """
    return next(iter(iterable), default) if iterable else default
