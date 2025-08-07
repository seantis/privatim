from __future__ import annotations
import uuid
from datetime import datetime
from typing import Annotated

from sqlalchemy import BigInteger
from sqlalchemy import Integer
from sqlalchemy import LargeBinary
from sqlalchemy import String
from sqlalchemy import Text as TextType
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import registry
from sqlalchemy.schema import MetaData
from sqlalchemy import DateTime
from sqlalchemy_file import FileField, File
from .utcdatetime_type import UTCDateTime
from .uuid_type import UUIDStr as UUIDStrType


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sqlalchemy.sql.schema import _NamingSchemaTD


# Recommended naming convention used by Alembic, as various different database
# providers will autogenerate vastly different names making migrations more
# difficult. See: https://alembic.sqlalchemy.org/en/latest/naming.html
NAMING_CONVENTION: '_NamingSchemaTD' = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)


# Some commonly used columns
UUIDStrPK = Annotated[str, mapped_column(
    UUIDStrType,
    primary_key=True,
    default=uuid.uuid4
)]
BigIntPK = Annotated[
    int,
    mapped_column(
        BigInteger().with_variant(Integer(), 'sqlite'), primary_key=True
    ),
]
BigInt = Annotated[int, 'BigInt']
DateTimeWithoutTz = Annotated[datetime, 'DateTimeWithoutTz']
DateTimeWithTz = Annotated[datetime, 'DateTimeWithTz']
UUIDStr = Annotated[str, 'UUIDStr']
str_32 = Annotated[str, 32]
str_64 = Annotated[str, 64]
str_128 = Annotated[str, 128]
str_256 = Annotated[str, 256]
Text = Annotated[str, 'Text']
FileContents = Annotated[bytes, 'File']

# File attachments that are stored on the filesystem and managed through
# sqlalchemy_file.
AttachedFile = Annotated[File, 'AttachedFile']


class Base(DeclarativeBase):

    metadata = metadata
    registry = registry(
        type_annotation_map={
            UUIDStr: UUIDStrType,
            datetime: UTCDateTime,
            BigInt: BigInteger().with_variant(Integer(), 'sqlite'),
            str_32: String(length=32),
            str_64: String(length=64),
            str_128: String(length=128),
            str_256: String(length=256),
            DateTimeWithoutTz: DateTime(timezone=False),
            Text: TextType,
            FileContents: LargeBinary,
            AttachedFile: FileField,
        }
    )
