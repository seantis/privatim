from typing import Any

from pyramid.httpexceptions import HTTPBadRequest, HTTPForbidden, HTTPNotFound

NotFound = HTTPNotFound
Forbidden = HTTPForbidden

class BadCSRFToken(HTTPBadRequest): ...
class PredicateMismatch(HTTPNotFound): ...
class URLDecodeError(UnicodeDecodeError): ...
class ConfigurationError(Exception): ...

class ConfigurationConflictError(ConfigurationError):
    def __init__(self, conflicts: dict[str, list[Any]]) -> None: ...

class ConfigurationExecutionError(ConfigurationError):
    etype: type[BaseException]
    evalue: BaseException
    info: Any
    def __init__(self, etype: type[BaseException], evalue: BaseException, info: Any) -> None: ...

class CyclicDependencyError(Exception):
    cycles: dict[Any, list[Any]]
    def __init__(self, cycles: dict[Any, list[Any]]) -> None: ...
