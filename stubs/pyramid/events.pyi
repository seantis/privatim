from zope.interface import implementer

from pyramid.interfaces import IContextFound, INewRequest, INewResponse, IRequest, IResponse

@implementer(INewRequest)
class NewRequest:
    request: IRequest
    def __init__(self, request: IRequest) -> None: ...

@implementer(INewResponse)
class NewResponse:
    request: IRequest
    response: IResponse
    def __init__(self, request: IRequest, response: IResponse) -> None: ...

@implementer(IContextFound)
class ContextFound:
    request: IRequest
    def __init__(self, request: IRequest) -> None: ...
