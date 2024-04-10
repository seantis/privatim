from typing import Any

from pyramid.interfaces import IRequestFactory
from pyramid.interfaces import IResponseFactory
from pyramid.interfaces import IRootFactory
from pyramid.interfaces import ISessionFactory


class FactoriesConfiguratorMixin:
    def set_root_factory(self, factory: IRootFactory) -> None: ...
    def set_session_factory(self, factory: ISessionFactory) -> None: ...
    def set_request_factory(self, factory: IRequestFactory) -> None: ...
    def set_response_factory(self, factory: IResponseFactory) -> None: ...
    def add_request_method(
        self,
        callable: Any | None = ...,
        name: str | None = ...,
        property: bool = ...,
        reify: bool = ...
    ) -> None: ...
