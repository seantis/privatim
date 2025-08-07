from webob.response import Response as _Response
from zope.interface import implementer

from pyramid.interfaces import IRequest
from pyramid.interfaces import IResponse

@implementer(IResponse)
class Response(_Response): ...

class FileResponse(Response):
    def __init__(
        self,
        path: str,
        request: IRequest | None = ...,
        cache_max_age: int | None = ...,
        content_type: str | None = ...,
        content_encoding: str | None = ...
    ): ...
