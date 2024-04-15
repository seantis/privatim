from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Table, Column, ForeignKey
from privatim.orm import Base


user_group_association = Table(
    'user_group_association',
    Base.metadata,
    Column(
        'group_id',
        UUID(as_uuid=True),
        ForeignKey('groups.id'),
        index=True,
        primary_key=True,
    ),
    Column(
        'user_id',
        UUID(as_uuid=True),
        ForeignKey('user.id'),
        index=True,
        primary_key=True,
    ),
)
