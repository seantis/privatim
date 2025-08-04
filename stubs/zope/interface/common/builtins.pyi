from _typeshed import SupportsRichComparison
from collections.abc import Callable
from typing import Any, overload

from zope.interface import classImplements
from zope.interface.common import collections, io, numbers

__all__ = ["IList", "ITuple", "ITextString", "IByteString", "INativeString", "IBool", "IDict", "IFile"]

class IList(collections.IMutableSequence):
    @overload
    def sort(*, key: None = None, reverse: bool = False) -> None: ...
    @overload
    def sort(*, key: Callable[[Any], SupportsRichComparison], reverse: bool = False) -> None: ...

class ITuple(collections.ISequence): ...
class ITextString(collections.ISequence): ...
class IByteString(collections.IByteString): ...
class INativeString(ITextString): ...
class IBool(numbers.IIntegral): ...
class IDict(collections.IMutableMapping): ...
class IFile(io.IIOBase): ...

classImplements(list, IList)
classImplements(tuple, ITuple)
classImplements(str, ITextString)
classImplements(bytes, IByteString)
classImplements(str, INativeString)
classImplements(bool, IBool)
classImplements(dict, IDict)
