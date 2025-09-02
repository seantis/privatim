from _typeshed.wsgi import StartResponse
from _typeshed.wsgi import WSGIEnvironment
from collections.abc import Callable
from collections.abc import Collection
from collections.abc import Iterable
from collections.abc import Iterator
from collections.abc import Mapping
from collections.abc import MutableMapping
from collections.abc import Sequence
from contextlib import contextmanager
from privatim.flash import MessageQueue
from privatim.models import User
# We overwrite this!
from privatim.orm.session import FilteredSession as DBSession
from types import ModuleType
from types import TracebackType
from typing import Any
from typing import TypedDict
from typing_extensions import TypeAlias
from webob.multidict import GetDict
from webob.request import Request as _Request
from webob.response import Response as _Response
from zope.interface import Interface

from pyramid_layout.interfaces import ILayoutManager
from pyramid.registry import Registry
from pyramid.security import ACLPermitsResult

_HTTPHeader: TypeAlias = tuple[str, str]

class _RouteMapResult(TypedDict):
    route: IRoute | None
    match: dict[str, str] | None

class IContextFound(Interface):
    request: IRequest

IAfterTraversal = IContextFound

class IBeforeTraversal(Interface):
    request: IRequest

class INewRequest(Interface):
    request: IRequest

class INewResponse(Interface):
    request: IRequest
    response: IResponse

class IApplicationCreated(Interface):
    app: IRouter

IWSGIApplicationCreatedEvent = IApplicationCreated
class IResponse(Interface, _Response): ...

class IExceptionResponse(IResponse):
    def prepare(environ: dict[str, Any]) -> None: ...

class ISecurityPolicy(Interface):
    def identity(request: IRequest) -> Any | None: ...
    def authenticated_userid(request: IRequest) -> str | None: ...
    def permits(
        request: IRequest,
        context: Any,
        permission: str
    ) -> ACLPermitsResult: ...
    def remember(
        request: IRequest,
        userid: str,
        **kw: Any
    ) -> list[_HTTPHeader]: ...
    def forget(request: IRequest, **kw: Any) -> list[_HTTPHeader]: ...

class IAuthenticationPolicy(Interface):
    def authenticated_userid(request: IRequest) -> str | None: ...
    def unauthenticated_userid(request: IRequest) -> str | None: ...
    def effective_principals(request: IRequest) -> list[str]: ...
    def remember(
        request: IRequest,
        userid: str,
        **kw: Any
    ) -> list[_HTTPHeader]: ...
    def forget(request: IRequest) -> list[_HTTPHeader]: ...

class IAuthorizationPolicy(Interface):
    def permits(
        context: Any,
        principals: Collection[str],
        permission: str
    ) -> ACLPermitsResult: ...
    def principals_allowed_by_permission(
        context: Any,
        permission: str
    ) -> list[str]: ...

class IRootFactory(Interface):
    def __call__(request: IRequest) -> Any: ...

class IDefaultRootFactory(Interface):
    def __call__(request: IRequest) -> Any: ...

class IRouter(Interface):
    registry: Registry
    @contextmanager
    def request_context(
        self, environ: dict[str, Any]
    ) -> Iterator[IRequest]: ...
    def invoke_request(request: IRequest) -> IResponse: ...
    # NOTE: Technically not part of the interface, but it should be
    def __call__(env: WSGIEnvironment, start_response: StartResponse) -> Iterable[bytes]: ...

class IRoutePregenerator(Interface):
    def __call__(
        request: IRequest,
        elements: Sequence[str],
        kwargs: Mapping[str, str]
    ) -> tuple[Sequence[str], Mapping[str, str]]: ...

class IRoute(Interface):
    name: str
    pattern: str
    factory: IRootFactory | None
    predicates: Sequence[IPredicate]
    pregenerator: IRoutePregenerator | None
    def match(path: str) -> dict[str, str] | None: ...
    def generate(kwargs: dict[str, str]) -> str:  ...

class IRoutesMapper(Interface):
    def get_routes() -> Sequence[IRoute]: ...
    def has_routes() -> bool: ...
    def get_route(name: str) -> IRoute | None: ...
    def connect(
        name: str,
        pattern: str,
        factory: IRootFactory | None = ...,
        predicates: Sequence[IPredicate] = ...,
        pregenerator: IRoutePregenerator | None = ...,
        static: bool = ...,
    ) -> None: ...
    def generate(name: str, kw: dict[str, Any]) -> str: ...
    def __call__(request: IRequest) -> _RouteMapResult: ...

class IRequest(Interface, _Request):
    # NOTE: This mostly contains convenience attributes
    #       that are not actually part of the interface
    exception: Exception | None
    exc_info: tuple[type[Exception], Exception, TracebackType] | None
    matchdict: dict[str, str]
    matched_route: IRoute
    locale_name: str
    localizer: ILocalizer
    timezone: str
    registry: Registry
    session: ISession
    context: Any
    dbsession: DBSession
    tm: Any

    # NOTE: technically these can be None but since most views are
    #       authenticated we assume that they are always set, we
    #       can override the type for the few views that are
    #       unauthenticated and need to access this
    authenticated_userid: str
    user: User

    messages: MessageQueue
    response: IResponse
    layout_manager: ILayoutManager

    # NOTE: For simplicity we assume POST/params cannot contain
    #       FieldStorage, even though they could.
    @property
    def POST(self) -> GetDict: ...  # type:ignore[override]
    @property
    def params(self) -> GetDict: ...  # type:ignore[override]

    def route_url(
        route_name: str,
        *,
        _query: Mapping[str, str | list[str]] | None = ...,
        _anchor: str | None = ...,
        **kwargs: Any
    ) -> str: ...

    def route_path(
        route_name: str,
        *,
        _query: Mapping[str, str | list[str]] | None = ...,
        _anchor: str | None = ...,
        **kwargs: Any
    ) -> str: ...

    def current_route_url(
        *,
        _query: Mapping[str, str | list[str]] | None = ...,
        _anchor: str | None = ...,
        **kwargs: Any
    ) -> str: ...

    def current_route_path(
        *,
        _query: Mapping[str, str | list[str]] | None = ...,
        _anchor: str | None = ...,
        **kwargs: Any
    ) -> str: ...

    def static_url(path: str) -> str: ...
    def static_path(path: str) -> str: ...

    def has_permission(permission: str, context: Any | None = ...) -> bool: ...

class IRequestHandler(Interface):
    def __call__(
        request: IRequest
    ) -> tuple[IRequest, IResponse]: ...

class ILocalizer(Interface):
    locale_name: str
    def translate(
        tstring: str,
        domain: str | None = ...,
        mapping: dict[str, Any] | None = ...
    ) -> str: ...
    def pluralize(
        singular: str,
        plural: str,
        n: int,
        domain: str | None = ...,
        mapping: dict[str, Any] | None = ...
    ) -> str: ...

class ITranslationDirectories(Interface): ...

class ICSRFStoragePolicy(Interface):
    def new_csrf_token(request: IRequest) -> str: ...
    def get_csrf_token(request: IRequest) -> str: ...
    def check_csrf_token(request: IRequest, token: str) -> bool: ...

class ISession(Interface, dict[str, Any]):  # type:ignore[misc]
    created: int
    new: bool
    def invalidate() -> None: ...
    def changed() -> None: ...
    def flash(
        msg: Any,
        queue: str = ...,
        allow_duplicate: bool = ...
    ) -> None: ...
    def pop_flash(queue: str = ...) -> list[Any]: ...
    def peek_flash(queue: str = ...) -> list[Any]: ...

    # convenience attributes not part of the interface
    id: str
    def get_csrf_token() -> str: ...
    def regenerate_id() -> None: ...
    def get_by_id(id: str | None) -> ISession | None: ...
    def save() -> None: ...

class ISessionFactory(Interface):
    def __call__(request: IRequest) -> ISession: ...

class IRendererInfo(Interface):
    name: str
    packages: ModuleType
    registry: Registry
    settings: MutableMapping[str, str]
    type: str
    def clone() -> IRendererInfo: ...

class _RendererSystemInfo(TypedDict):
    view: Callable[[Any, IRequest], Any]
    renderer_name: str
    context: Any
    request: IRequest

class IRenderer(Interface):
    def __call__(value: Any, system: _RendererSystemInfo) -> str: ...

class IRendererFactory(Interface):
    def __call__(info: IRendererInfo) -> IRenderer: ...

class IRequestFactory(Interface):
    def __call__(environ: dict[str, Any]) -> IRequest: ...
    def blank(str: str) -> IRequest: ...

class IResponseFactory(Interface):
    def __call__(request: IRequest) -> IResponse: ...

class IViewMapper(Interface):
    def __call__(object: Any) -> Callable[[Any, IRequest], IResponse]: ...

class IViewMapperFactory(Interface):
    def __call__(**kwargs: Any) -> IViewMapper: ...

class IPredicate(Interface):
    def text() -> str: ...
    def phash() -> str: ...

class IPredicateList(Interface, list[IPredicate]): ...  # type:ignore[misc]

class IPredicateInfo(Interface):
    package: ModuleType
    registry: Registry
    settings: MutableMapping[str, str]
    def maybe_dotted(value: str) -> Any: ...

class IPredicateFactory(Interface):
    def __call__(value: Any, info: IPredicateInfo) -> IPredicate: ...

class _RouteInfo(TypedDict):
    match: dict[str, str]
    route: IRoute

class IRoutePredicate(IPredicate):
    def __call__(info: _RouteInfo, request: IRequest) -> bool: ...

class ISubscriberPredicate(IPredicate):
    def __call__(event: Any) -> bool: ...

class IViewPredicate(IPredicate):
    def __call__(context: Any, request: IRequest) -> bool: ...

class ICacheBuster(Interface):
    def __call__(
        request: IRequest,
        subpath: str,
        kw: dict[str, Any]
    ) -> tuple[str, dict[str, Any]]: ...
