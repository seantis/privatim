from datetime import datetime
from sedate import standardize_date, to_timezone
from sqlalchemy.types import DateTime, TypeDecorator


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sqlalchemy.engine.interfaces import Dialect


class UTCDateTime(TypeDecorator[datetime]):
    """ Stores dates as UTC.

    Internally, they are stored as timezone naive, because Postgres takes
    the local timezone into account when working with timezones. Values taken
    and values returned are forced to be timezone-aware though.

    """

    impl = DateTime
    cache_ok = True

    def __init__(self) -> None:
        super().__init__(timezone=False)

    def process_bind_param(
        self,
        value: datetime | None,
        dialect: 'Dialect'
    ) -> datetime | None:

        if value is None:
            return None
        return to_timezone(value, 'UTC').replace(tzinfo=None)

    def process_result_value(
        self,
        value: datetime | None,
        dialect: 'Dialect'
    ) -> datetime | None:

        if value is None:
            return None
        return standardize_date(value, timezone='UTC')
