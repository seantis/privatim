from collections.abc import Callable
from collections.abc import Iterable

from pyramid.interfaces import IAuthenticationPolicy
from pyramid.interfaces import IAuthorizationPolicy
from pyramid.interfaces import ICSRFStoragePolicy
from pyramid.interfaces import IRequest
from pyramid.interfaces import ISecurityPolicy


class SecurityConfiguratorMixin:
    def set_security_policy(self, policy: ISecurityPolicy | str) -> None: ...
    def set_authentication_policy(
        self,
        policy: IAuthenticationPolicy | str
    ) -> None: ...
    def set_authorization_policy(
        self,
        policy: IAuthorizationPolicy | str
    ) -> None: ...
    def set_default_permission(self, permission: str) -> None: ...
    def add_permission(self, permission_name: str) -> None: ...
    def set_default_csrf_options(
        self,
        require_csrf: bool = ...,
        token: str = ...,
        header: str = ...,
        safe_methods: Iterable[str] = ...,
        check_origin: bool = ...,
        allow_no_origin: bool = ...,
        callback: Callable[[IRequest], bool] | None = ...
    ) -> None: ...
    def set_csrf_storage_policy(
        self,
        policy: ICSRFStoragePolicy | str
    ) -> None: ...
