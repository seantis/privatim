from enum import Enum
from functools import wraps
from pyramid.threadlocal import get_current_request


from typing import Any, TypeVar, TYPE_CHECKING
if TYPE_CHECKING:
    from collections.abc import Callable
    from typing_extensions import ParamSpec

    _P = ParamSpec('_P')

_T = TypeVar('_T')


class _Marker(Enum):
    EMPTY = 0


_EMPTY = _Marker.EMPTY


def instance_cache() -> 'Callable[[Callable[_P, _T]], Callable[_P, _T]]':
    """
    Decorator for caching method results on the instance.
    """

    def decorating_function(
        user_function: 'Callable[_P, _T]'
    ) -> 'Callable[_P, _T]':

        @wraps(user_function)
        def wrapper(*args: '_P.args', **kwds: '_P.kwargs') -> _T:
            instance = args[0]
            cache = getattr(instance, '_cache', None)
            if cache is None:
                instance._cache = cache = {}  # type:ignore[attr-defined]

            key = (user_function.__name__, args, frozenset(kwds.items()))
            result = cache.get(key, _EMPTY)
            if result is _EMPTY:
                result = user_function(*args, **kwds)
                cache[key] = result
            return result

        def cache(instance: object) -> dict[Any, Any]:
            cache = getattr(instance, '_cache', None)
            if cache is None:
                cache = {}
            return cache

        wrapper.cache = cache  # type:ignore[attr-defined]
        return wrapper

    return decorating_function


def clear_instance_cache(instance: object) -> None:
    if getattr(instance, '_cache', None):
        instance._cache = {}  # type:ignore[attr-defined]


def request_cache() -> 'Callable[[Callable[_P, _T]], Callable[_P, _T]]':
    """
    Caches objects on the request.
    """

    def decorating_function(
        user_function: 'Callable[_P, _T]'
    ) -> 'Callable[_P, _T]':

        @wraps(user_function)
        def wrapper(*args: '_P.args', **kwds: '_P.kwargs') -> _T:
            request = get_current_request()
            if request is None:
                return user_function(*args, **kwds)
            cache = getattr(request, 'cache', None)
            if cache is None:
                request.cache = cache = {}
            key = (user_function.__name__, args, frozenset(kwds.items()))
            result = cache.get(key, _EMPTY)
            if result is _EMPTY:
                result = user_function(*args, **kwds)
                cache[key] = result
            return result

        def cache_clear() -> None:
            request = get_current_request()
            if request:
                request.cache = {}

        wrapper.cache_clear = cache_clear  # type:ignore[attr-defined]
        return wrapper

    return decorating_function
