from collections.abc import Callable, Sequence
from types import ModuleType
from typing import Any, Protocol
from zope.interface.registry import Components

from pyramid.interfaces import IRenderer, IRendererInfo, IRequest, IResponse
from pyramid.registry import Registry

# NOTE: Technically this can return bytes or Iterator[bytes] depending on the renderer
#       but we only pass chameleon templates, so for now we assume it always returns str
#       if we wanted to fix this we should probably write a plugin to infer the return type
#       based on the renderer_name
def render(renderer_name: str, value: object, request: IRequest | None = None, package: ModuleType | str | None = None) -> str: ...
def render_to_response(renderer_name: str, value: object, request: IRequest | None = None, package: ModuleType | str | None = None, response: IResponse | None = None) -> IResponse: ...
def get_renderer(renderer_name: str, package: ModuleType | str | None = None, registry: Registry | None = None) -> IRenderer: ...

# we don't bother annotating the default renderers we don't access directly
class _JSONSerializer(Protocol):
    def __call__(self, obj: object, /, *, default: Callable[[object], str] = ...) -> str: ...

class JSON:
    serializer: _JSONSerializer
    kw: dict[str, Any]
    components: Components
    def __init__(self, serializer: _JSONSerializer = ..., adapters: Sequence[tuple[type[object], Callable[[Any, IRequest], str]]] = (), **kw: Any) -> None: ...
    def add_adapter(self, type_or_iface: type[object], adapter: Callable[[Any, IRequest], str]) -> None: ...
    def __call__(self, info: IRendererInfo) -> IRenderer: ...
    def _make_default(self, request: IRequest) -> Callable[[object], str]: ...
