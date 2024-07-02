from typing import TYPE_CHECKING, Iterator
if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from sqlalchemy.orm import InstrumentedAttribute
    from privatim.orm.meta import UUIDStrPK
    from sqlalchemy.ext.hybrid import hybrid_property
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

    class HasSearchableFields(Protocol):
        id: UUIDStrPK

        @classmethod
        def searchable_fields(cls) -> Iterator['InstrumentedAttribute[str]']:
            ...

        @hybrid_property
        def searchable_text(self) -> str:
            ...
