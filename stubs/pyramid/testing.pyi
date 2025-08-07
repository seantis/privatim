from collections.abc import Iterator, MutableMapping, Sequence
from contextlib import contextmanager
from types import ModuleType
from typing import Any, Literal
from typing_extensions import Self
from webob.acceptparse import _AcceptProperty
from zope.interface import implementer

from pyramid.config import Configurator
from pyramid.interfaces import IRequest, IResponse, ISession
from pyramid.registry import Registry

class DummyRootFactory:
    def __init__(self, request: IRequest) -> None: ...
    def __getattr__(self, name: str) -> str: ...

class DummySecurityPolicy:
    userid: str | None
    _identity: Any | None
    permissive: bool
    remember_result: list[tuple[str, str]]
    forget_result: list[tuple[str, str]]
    def __init__(self, userid: str | None = None, identity: Any | None = None, permissive: bool = True, remember_result: list[tuple[str, str]] | None = None, forget_result: list[tuple[str, str]] | None = None) -> None: ...
    def identity(self, request: IRequest) -> Any | None: ...
    def authenticated_userid(self, request: IRequest) -> str | None: ...
    def permits(self, request: IRequest, context: Any, permission: str) -> bool: ...
    def remember(self, request: IRequest, userid: str, **kw: Any) -> list[tuple[str, str]]: ...
    def forget(self, request: IRequest, **kw: Any) -> list[tuple[str, str]]: ...

class DummyTemplateRenderer:
    def __init__(self, string_response: str = '') -> None: ...
    def implementation(self) -> MockTemplate: ...
    def __call__(self, kw: dict[str, Any], system: dict[str, Any] | None = None) -> str: ...
    def assert_(self, **kw: object) -> Literal[True]: ...

@implementer(ISession)
class DummySession(dict[str, Any]):  # type:ignore[misc]
    created: None
    new: Literal[True]
    def changed(self) -> None: ...
    def invalidate(self) -> None: ...
    def flash(self, msg: str, queue: str = '', allow_duplicate: bool = True) -> None: ...
    def pop_flash(self, queue: str = '') -> list[str]: ...
    def peek_flash(self, queue: str = '') -> list[str]: ...
    def new_csrf_token(self) -> str: ...
    def get_csrf_token(self) -> str: ...

@implementer(IRequest)
class DummyRequest:
    method: str
    application_url: str
    host: str
    domain: str
    content_length: int
    query_string: str
    charset: str
    script_name: str
    environ: dict[str, Any]
    headers: dict[str, str]
    params: MutableMapping[str, Any]
    cookies: dict[str, Any]
    matchdict: dict[str, str]
    GET: MutableMapping[str, Any]
    POST: MutableMapping[str, Any]
    host_url: str
    path_url: str
    url: str
    path: str
    path_info: str
    subpath: Sequence[str]
    traversed: Sequence[str]
    virtual_root_path: Sequence[str]
    context: Any
    root: None
    virtual_root: None
    marshalled: MutableMapping[str, Any]
    session: DummySession
    def __init__(
        self,
        params: MutableMapping[str, Any] | None = None,
        environ: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        path: str = '/',
        cookies: dict[str, Any] | None = None,
        post: MutableMapping[str, Any] | None = None,
        accept: Any | None = None,
        **kw: Any
    ) -> None: ...
    def __getattr__(self, name: str) -> Any: ...
    registry: Registry
    accept: _AcceptProperty
    response: IResponse

def setUp(
    registry: Registry | None = None,
    request: IRequest | None = None,
    hook_zca: bool = True,
    autocommit: bool = True,
    settings: dict[str, Any] | None = None,
    package: ModuleType | str | None = None
) -> Configurator: ...
def tearDown(unhook_zca: bool = True) -> None: ...

class MockTemplate:
    response: IResponse
    def __init__(self, response: IResponse) -> None: ...
    def __getattr__(self, attrname: str) -> Self: ...
    def __getitem__(self, attrname: str) -> Self: ...
    def __call__(self, *arg: object, **kw: object) -> IResponse: ...

@contextmanager
def testConfig(
    registry: Registry | None = None,
    request: IRequest | None = None,
    hook_zca: bool = True,
    autocommit: bool = True,
    settings: dict[str, Any] | None = None,
    package: ModuleType | str | None = None
) -> Iterator[Configurator]: ...
