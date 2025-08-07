from collections.abc import Callable
from collections.abc import Mapping
from collections.abc import Sequence
from logging import Logger
from types import ModuleType
from types import TracebackType
from typing import Any
from typing import TypedDict
from typing_extensions import Self
from zope.interface import Interface

from pyramid.config.adapters import AdaptersConfiguratorMixin
from pyramid.config.factories import FactoriesConfiguratorMixin
from pyramid.config.i18n import I18NConfiguratorMixin
from pyramid.config.predicates import not_ as not_
from pyramid.config.predicates import PredicateConfiguratorMixin
from pyramid.config.rendering import RenderingConfiguratorMixin
from pyramid.config.routes import RoutesConfiguratorMixin
from pyramid.config.security import SecurityConfiguratorMixin
from pyramid.config.settings import SettingsConfiguratorMixin
from pyramid.config.testing import TestingConfiguratorMixin
from pyramid.config.views import _View
from pyramid.config.views import ViewsConfiguratorMixin
from pyramid.interfaces import IAuthenticationPolicy
from pyramid.interfaces import IAuthorizationPolicy
from pyramid.interfaces import ILocaleNegotiator
from pyramid.interfaces import IRendererFactory
from pyramid.interfaces import IRequest
from pyramid.interfaces import IRequestFactory
from pyramid.interfaces import IResponse
from pyramid.interfaces import IResponseFactory
from pyramid.interfaces import IRootFactory
from pyramid.interfaces import IRouter
from pyramid.interfaces import ISecurityPolicy
from pyramid.interfaces import ISessionFactory
from pyramid.interfaces import IViewMapperFactory
from pyramid.path import Resolver
from pyramid.registry import Registry

class _ConfigurationContext(TypedDict):
    registry: Registry
    request: IRequest

# NOTE: We skip some of the mixins as we don't use them
class Configurator(
    # ActionConfiguratorMixin,
    PredicateConfiguratorMixin,
    TestingConfiguratorMixin,
    # TweensConfiguratorMixin,
    SecurityConfiguratorMixin,
    ViewsConfiguratorMixin,
    RoutesConfiguratorMixin,
    # ZCAConfiguratorMixin,
    I18NConfiguratorMixin,
    RenderingConfiguratorMixin,
    # AssetsConfiguratorMixin,
    SettingsConfiguratorMixin,
    FactoriesConfiguratorMixin,
    AdaptersConfiguratorMixin
):
    basepath: str | None
    includepath: tuple[str, ...]
    info: str
    name_resolver: Resolver
    package_name: str
    package: ModuleType
    root_package: ModuleType
    registry: Registry
    autocommit: bool
    route_prefix: str | None
    introspection: bool
    def __init__(
        self,
        registry: Registry | None = ...,
        package: ModuleType | str | None = ...,
        settings: Mapping[str, str] | None = ...,
        root_factory: IRootFactory | Callable[[IRequest], Any] | str | None = ...,
        security_policy: ISecurityPolicy | str | None = ...,
        authentication_policy: IAuthenticationPolicy | str | None = ...,
        authorization_policy: IAuthorizationPolicy | str | None = ...,
        renderers: list[IRendererFactory | str] | None = ...,
        debug_logger: Logger | str | None = ...,
        locale_negotiator: ILocaleNegotiator | str | None = ...,
        request_factory: IRequestFactory | str | None = ...,
        response_factory: IResponseFactory | str | None = ...,
        default_permission: str | None = ...,
        session_factory: ISessionFactory | str | None = ...,
        default_view_mapper: IViewMapperFactory | str | None = ...,
        autocommit: bool = ...,
        exceptionresponse_view: Callable[[Any, IRequest], IResponse] | str | None = ...,
        route_prefix: str | None = ...,
        introspection: bool = ...,
        root_package: ModuleType | str | None = ...
    ) -> None: ...
    def include(
        self,
        callable: Callable[[Configurator], None] | ModuleType | str,
        route_prefix: str | None = ...
    ) -> None: ...
    def with_package(self, package: ModuleType | str) -> Self: ...
    def begin(self, request: IRequest = ...) -> None: ...
    def end(self) -> _ConfigurationContext: ...
    def __enter__(self) -> Self: ...
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_traceback: TracebackType | None
    ) -> None: ...
    def scan(
        self,
        package: ModuleType | str | None = ...,
        categories: Sequence[str] = ...,
        onerror: Callable[[str], None] | None = ...,
        ignore: str | Callable[[str], bool] | Sequence[str] | None = ...,
    ) -> None: ...
    def make_wsgi_app(self) -> IRouter: ...

    # NOTE: Below we add methods that pyramid_layout adds to the
    #       Configurator
    def add_layout(
        self,
        layout: type | str | None = ...,
        template: str = ...,
        name: str | None = ...,
        context: type | Interface | str | None = ...,
    ) -> None: ...
    def add_panel(
        self,
        panel: _View | str,
        *,
        renderer: str | None = ...,
        name: str | None = ...,
        context: type | Interface | str | None = ...,
    ) -> None: ...
