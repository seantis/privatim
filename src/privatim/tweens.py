from __future__ import annotations
from .git_info import get_git_revision_hash


from typing import TYPE_CHECKING, Any
from collections.abc import Callable
if TYPE_CHECKING:
    from pyramid.request import Request
    from pyramid.response import Response


def git_info_tween_factory(
    handler: Callable[['Request'], 'Response'], registry: Any
) -> Callable[['Request'], 'Response']:
    def git_info_tween(request: 'Request') -> 'Response':
        request.git_revision = get_git_revision_hash()
        return handler(request)

    return git_info_tween
