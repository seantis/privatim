from typing import Callable, Any
from pyramid.request import Request
from pyramid.response import Response
from .git_info import get_git_revision_hash


def git_info_tween_factory(
    handler: Callable[[Request], Response], registry: Any
) -> Callable[[Request], Response]:
    def git_info_tween(request: Request) -> Response:
        request.git_revision = get_git_revision_hash()
        return handler(request)

    return git_info_tween
