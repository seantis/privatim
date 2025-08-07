from collections.abc import Sequence
from typing import Any, ClassVar, Final, Literal
from typing_extensions import Self

from pyramid.interfaces import IRequest

from privatim.types import ACL as ACLEntry

NO_PERMISSION_REQUIRED: Final = "__no_permission_required__"
def remember(request: IRequest, userid: str, **kw: Any) -> list[tuple[str, str]]: ...
def forget(request: IRequest, **kw: Any) -> list[tuple[str, str]]: ...

class PermitsResult(int):
    boolval: ClassVar[int]
    s: str
    args: tuple[Any, ...]
    def __new__(cls, s: str, *args: Any) -> Self: ...
    @property
    def msg(self) -> str: ...

class Denied(PermitsResult):
    boolval: ClassVar[Literal[0]]
    def __bool__(self) -> Literal[False]: ...

class Allowed(PermitsResult):
    boolval: ClassVar[Literal[1]]
    def __bool__(self) -> Literal[True]: ...

class ACLPermitsResult(PermitsResult):
    permission: str
    ace: ACLEntry | str
    acl: Sequence[ACLEntry]
    principals: list[str]
    context: Any
    def __new__(cls, ace: ACLEntry | str, acl: Sequence[ACLEntry], permission: str, principals: list[str], context: Any) -> Self: ...
