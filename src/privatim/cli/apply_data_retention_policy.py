from datetime import timedelta

import click
from pyramid.paster import bootstrap
from pyramid.paster import get_appsettings
from sedate import utcnow
from sqlalchemy import delete

from privatim.models import Consultation
from privatim.models.soft_delete import SoftDeleteMixin
from privatim.orm import get_engine, Base


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sqlalchemy.orm.session import Session


KEEP_DELETED_FILES_TIMESPAN = 30


def delete_old_records(
        session: 'Session',
        model: type[Base],
        days_threshold: int = 30
) -> list[str]:
    if not issubclass(model, SoftDeleteMixin):
        raise ValueError(f'{model.__name__} does not support soft delete')

    cutoff_date = utcnow() - timedelta(days=days_threshold)

    # Combine the select and delete operations
    stmt = (
        delete(model)
        .where(
            model.updated <= cutoff_date,  # type:ignore[attr-defined]
            model.deleted.is_(True)
        )
        .returning(model.id)  # type:ignore[attr-defined]
    )
    result = session.execute(stmt)
    deleted_ids = result.scalars().all()
    session.flush()
    return deleted_ids


@click.command()
@click.argument('config_uri')
def hard_delete(
        config_uri: str,
) -> None:
    env = bootstrap(config_uri)
    settings = get_appsettings(config_uri)
    engine = get_engine(settings)
    Base.metadata.create_all(engine)

    with env['request'].tm:
        session = env['request'].dbsession
        deleted_consultation_ids = delete_old_records(session, Consultation)
        for id in deleted_consultation_ids:
            print(f"Deleted Consultation with ID: {id}")


if __name__ == '__main__':
    hard_delete()
