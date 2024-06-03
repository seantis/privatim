from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship, joinedload, Mapped
from typing import TypeVar
from sqlalchemy.orm import object_session

from .utils import QueryChain


from typing import Any, Literal, NamedTuple, TYPE_CHECKING
if TYPE_CHECKING:
    from sqlalchemy.orm.query import Query
    from sqlalchemy.orm import DeclarativeBase as Base
    rel = relationship
    from .meta import UUIDStrPK

    Cardinality = Literal['one-to-many', 'one-to-one', 'many-to-many']


_M = TypeVar('_M', bound='Associable')


class RegisteredLink(NamedTuple):
    cls: type['Base']
    table: Table
    key: str
    attribute: str
    cardinality: 'Cardinality'

    @property
    def class_attribute(self) -> Any:
        return getattr(self.cls, self.attribute)


class Associable:
    """ Mixin to enable associations on a model. Only models which are
    associable may be targeted by :func:`associated`.

    """

    registered_links: dict[str, RegisteredLink] | None = None

    if TYPE_CHECKING:
        id: Mapped[UUIDStrPK]
        __tablename__: str

    @classmethod
    def association_base(cls) -> type['Associable']:
        """ Returns the model which directly inherits from Associable. """

        for parent in cls.__bases__:
            if parent is Associable:
                return cls
            if issubclass(parent, Associable):
                return parent.association_base()

        return cls

    @classmethod
    def register_link(
            cls,
            link_name: str,
            linked_class: type['Base'],
            table: Table,
            key: str,
            attribute: str,
            cardinality: 'Cardinality'
    ) -> None:
        """ All associated classes are registered through this method. This
        yields the following benefits:

        1. We gain the ability to query all the linked records in one query.
           This is hard otherwise as each ``Payable`` class leads to its own
           association table which needs to be queried separately.

        2. We are able to reset all created backreferences. This is necessary
           during tests. SQLAlchemy keeps these references around and won't
           let us re-register the same model multiple times (which outside
           of tests is completely reasonable).

        """
        base = cls.association_base()

        if not base.registered_links:
            base.registered_links = {}

        base.registered_links[link_name] = RegisteredLink(
            cls=linked_class,
            table=table,
            key=key,
            attribute=attribute,
            cardinality=cardinality
        )

    @property
    def links(self) -> 'QueryChain[Base]':
        """ Returns a query chain with all records of all models which attach
        to the associable model.

        """
        assert self.registered_links is not None, "No links registered"

        session = object_session(self)
        assert session is not None

        def query(link: RegisteredLink) -> 'Query[Base]':
            column = getattr(link.cls, link.attribute)

            q = session.query(link.cls)

            if column.property.uselist:
                q = q.filter(column.contains(self))
            else:
                q = q.filter(column == self)

            return q.options(joinedload(column))

        return QueryChain(tuple(
            query(link) for link in self.registered_links.values()
        ))


def associated(
        associated_cls: type[_M],
        attribute_name: str,
        *,
        backref_suffix: str = '__tablename__',
) -> Mapped[list[_M]]:

    """ Creates an associated attribute. This attribute is supposed to be
    defined on the mixin class that will establish the generic association
    if inherited by a model.

    Currently supports one-to-many relationships as that is the most common
    use case and the only one we need at the moment.
    Simplified version of onegov.core.orm.abstract.associable
    """

    def descriptor(cls: type['Base']) -> Mapped[list[_M]]:

        name = '{}_for_{}_{}'.format(
            associated_cls.__tablename__,
            cls.__tablename__,
            attribute_name
        )
        key = f'{cls.__tablename__}_id'
        target = f'{cls.__tablename__}.id'

        if backref_suffix == '__tablename__':
            backref_name = f'linked_{cls.__tablename__}'
        else:
            backref_name = f'linked_{backref_suffix}'

        association_key = associated_cls.__name__.lower() + '_id'
        association_id = associated_cls.id

        association_table = cls.metadata.tables.get(name)
        if association_table is None:
            association_table = Table(
                name,
                cls.metadata,
                Column(key,
                       ForeignKey(target),
                       nullable=False),
                Column(
                    association_key,
                    ForeignKey(association_id),
                    nullable=False
                )
            )

        assert issubclass(associated_cls, Associable)

        associated_cls.register_link(
            backref_name,
            cls,
            association_table,
            key,
            attribute_name,
            cardinality='one-to-many'
        )

        return relationship(
            argument=associated_cls,
            secondary=association_table,
            single_parent=True,
            cascade='all, delete-orphan',
            uselist=True,
            passive_deletes=False
        )

    return declared_attr(descriptor)  # type:ignore[return-value]
