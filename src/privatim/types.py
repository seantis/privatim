from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from privatim.models import Consultation, Meeting
    from decimal import Decimal
    from fractions import Fraction
    from pyramid.httpexceptions import (
        HTTPFound,
        HTTPForbidden,
        HTTPError,
        HTTPNotFound
    )
    from pyramid.interfaces import IResponse, IRequest

    from typing import Any, Literal, TypeVar, Protocol
    from typing_extensions import NotRequired, TypedDict, TypeAlias

    # Monkey patch (no effect)
    # from pyramid.request import Request
    # Request.dbsession: FilteredSession

    _Tco = TypeVar('_Tco', covariant=True)

    JSON: TypeAlias = (
        dict[str, 'JSON'] | list['JSON']
        | str | int | float | bool | None
    )
    JSONObject: TypeAlias = dict[str, JSON]
    JSONArray: TypeAlias = list[JSON]

    # read only variant of JSON type that is covariant
    JSON_ro: TypeAlias = (
        Mapping[str, 'JSON_ro'] | Sequence['JSON_ro']
        | str | int | float | bool | None
    )
    JSONObject_ro: TypeAlias = Mapping[str, JSON_ro]
    JSONArray_ro: TypeAlias = Sequence[JSON_ro]

    ACL: TypeAlias = tuple[Literal['Allow', 'Deny'], str, list[str]]

    HTMLParam = str | int | float | Decimal | Fraction | bool | None
    HTTPMethod = Literal[
        'GET',
        'POST',
        'PUT',
        'PATCH',
        'DELETE',
    ]

    RenderData: TypeAlias = dict[str, Any]
    RenderDataOrRedirect: TypeAlias = RenderData | HTTPFound
    RenderDataOrNotFound: TypeAlias = RenderData | HTTPNotFound
    RenderDataOrRedirectOrForbidden: TypeAlias = (
        RenderData | HTTPFound | HTTPForbidden | HTTPError
    )
    RenderDataOrResponse: TypeAlias = RenderData | IResponse
    ResponseOrNotFound: TypeAlias = IResponse | HTTPNotFound

    # NOTE: For now we only allow complex return types if we return JSON
    #       If you want to return a scalar type as JSON you need to be
    #       explicit about it.
    XHRData: TypeAlias = JSONObject_ro | JSONArray_ro
    XHRDataOrRedirect: TypeAlias = XHRData | HTTPFound
    XHRDataOrResponse: TypeAlias = XHRData | IResponse

    MixedData: TypeAlias = RenderData | XHRData
    MixedDataOrRedirect: TypeAlias = MixedData | HTTPFound
    MixedDataOrResponse: TypeAlias = MixedData | IResponse

    class FileDict(TypedDict):
        data: str
        filename: str | None
        mimetype: str
        size: int

    class LaxFileDict(TypedDict):
        data: str
        filename: NotRequired[str | None]
        mimetype: NotRequired[str]
        size: NotRequired[int]

    class Callback(Protocol[_Tco]):
        def __call__(self, context: Any, request: IRequest) -> _Tco: ...

    Activity: TypeAlias = Consultation | Meeting
