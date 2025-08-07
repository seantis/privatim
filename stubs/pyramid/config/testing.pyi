from collections.abc import Mapping
from typing import Any, TypeAlias, TypeVar, overload

from pyramid.interfaces import IRendererFactory
from pyramid.testing import DummySecurityPolicy

_T = TypeVar('_T')
_ResourcesT = TypeVar('_ResourcesT', bound=Mapping[str, object])
_HTTPHeader: TypeAlias = tuple[str, str]

class TestingConfiguratorMixin:
    def testing_securitypolicy(
        self,
        userid: str | None = None,
        identity: Any | None = None,
        permissive: bool = True,
        remember_result: list[_HTTPHeader] | None = None,
        forget_result: list[_HTTPHeader] | None = None,
    ) -> DummySecurityPolicy: ...
    def testing_resources(self, resources: _ResourcesT) -> _ResourcesT: ...
    @overload
    def testing_add_subscriber(self, event_iface: type[_T]) -> list[_T]: ...
    @overload
    def testing_add_subscriber(self, event_iface: str | None = None) -> list[Any]: ...
    def testing_add_renderer(
        self,
        path: str,
        renderer: IRendererFactory | str | None = None
    ) -> None: ...
    testing_add_template = testing_add_renderer
