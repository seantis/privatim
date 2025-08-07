from __future__ import annotations
from functools import wraps
from typing import Any
from typing import TypeVar
from typing import cast

from pyramid.threadlocal import get_current_request


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Hashable

F = TypeVar('F', bound='Callable[..., Any]')
_marker = object()


def instance_cache() -> 'Callable[[F], F]':
    """
    Decorator for caching method results on the instance.
    """

    def decorating_function(user_function: F) -> F:

        @wraps(user_function)
        def wrapper(*args: 'Hashable', **kwds: 'Hashable') -> Any:
            instance = args[0]
            cache = getattr(instance, '_cache', None)
            if cache is None:
                instance._cache = cache = {}  # type:ignore[attr-defined]

            key = (user_function.__name__, args, frozenset(kwds.items()))
            result = cache.get(key, _marker)
            if result is _marker:
                result = user_function(*args, **kwds)
                cache[key] = result
            return result

        def cache(instance: Any) -> dict[Any, Any]:
            cache = getattr(instance, '_cache', None)
            if cache is None:
                cache = {}
            return cache

        wrapper.cache = cache  # type:ignore[attr-defined]
        return cast('F', wrapper)

    return decorating_function


def clear_instance_cache(instance: Any) -> None:
    if getattr(instance, '_cache', None):
        instance._cache = {}


def request_cache() -> 'Callable[[F], F]':
    """
    Caches objects on the request.
    """

    def decorating_function(user_function: F) -> F:

        @wraps(user_function)
        def wrapper(*args: 'Hashable', **kwds: 'Hashable') -> Any:
            request = get_current_request()
            if request is None:
                return user_function(*args, **kwds)
            cache = getattr(request, 'cache', None)
            if cache is None:
                request.cache = cache = {}
            key = (user_function.__name__, args, frozenset(kwds.items()))
            result = cache.get(key, _marker)
            if result is _marker:
                result = user_function(*args, **kwds)
                cache[key] = result
            return result

        def cache_clear() -> None:
            request = get_current_request()
            if request:
                request.cache = {}

        wrapper.cache_clear = cache_clear  # type:ignore[attr-defined]
        return cast('F', wrapper)

    return decorating_function
