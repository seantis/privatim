from collections.abc import Callable
from functools import wraps
from sqlalchemy import Uuid
from uuid import UUID as _PythonUUID
from typing import Any
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy import Dialect

Processor = Callable[[Any], str | None]


def coerce_uuid_arg_to_str(proc: Processor) -> Processor:
    @wraps(proc)
    def processor(value: Any) -> str | None:
        if isinstance(value, _PythonUUID):
            value = str(value)
        return proc(value)
    return processor


class UUIDStr(Uuid[str]):

    def __init__(self) -> None:
        super().__init__(as_uuid=False)

    # NOTE: We want our literal/bind processors to be more lax
    #       so we add a pre-processor that would convert any
    #       UUIDs to string values first.

    def bind_processor(self, dialect: 'Dialect') -> Processor | None:
        proc = super().bind_processor(dialect)
        if proc is None:
            return None
        return coerce_uuid_arg_to_str(proc)

    # NOTE: The literal processor technically expects the passed value
    #       to be of the bound python type i.e. in this case str, so
    #       we have to force overwrite this.
    def literal_processor(  # type:ignore[override]
        self,
        dialect: 'Dialect'
    ) -> Processor | None:
        proc = super().literal_processor(dialect)
        if proc is None:
            return None
        return coerce_uuid_arg_to_str(proc)
