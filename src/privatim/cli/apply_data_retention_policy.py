from datetime import timedelta
import logging
import click
from pyramid.paster import bootstrap
from pyramid.paster import get_appsettings
from sedate import utcnow
from sqlalchemy import select
from sqlalchemy.sql import delete
from privatim.models import Consultation  # noqa: E402
from privatim.orm import get_engine, Base


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from privatim.orm import FilteredSession

from privatim.models.file import SearchableFile  # noqa: E402

log = logging.getLogger(__name__)


def format_consultation_tree(
    consultation: Consultation, level: int = 0
) -> list[str]:
    """Format a single consultation and its version history recursively."""
    tree_lines = []
    indent = '  ' * level
    version_status = 'LATEST' if consultation.is_latest() else 'OLD'
    tree_lines.append(
        f'{indent}├── {consultation.title} ({version_status}) '
        f'[ID: {consultation.id}]'
    )
    if consultation.previous_version:
        tree_lines.extend(
            format_consultation_tree(consultation.previous_version, level + 1)
        )
    return tree_lines


def delete_old_consultation_chains(
        session: 'FilteredSession',
        days_threshold: int = 30
) -> list[str]:
    """
    Delete entire consultation chains where the latest version is:
    1. Soft deleted
    2. Older than the threshold

    Returns the IDs of all deleted consultations.
    """

    cutoff_date = utcnow() - timedelta(days=days_threshold)

    with session.no_consultation_filter():
        with session.no_soft_delete_filter():

            # First find latest versions that are soft-deleted and old enough
            latest_query = (
                select(Consultation)
                .where(
                    Consultation.is_latest_version == 1,
                    Consultation.deleted.is_(True),
                    Consultation.created <= cutoff_date
                )
            )

            to_delete = session.execute(latest_query).scalars().all()
            ids_to_delete = []
            for latest in to_delete:
                # Log the tree structure before deletion
                tree_lines = format_consultation_tree(latest)
                log.info(
                    'Will delete consultation tree:'
                    '\n%s', '\n'.join(tree_lines))

                # Follow chain backwards and collect IDs
                current: Consultation | None = latest
                while current is not None:
                    ids_to_delete.append(current.id)
                    current = current.previous_version

            if ids_to_delete:
                # First, delete associated SearchableFile records
                # to prevent ForeignKeyViolation during bulk Consultation 
                # delete.
                bulk_delete_files_stmt = delete(SearchableFile).where(
                    SearchableFile.consultation_id.in_(ids_to_delete)
                )
                session.execute(bulk_delete_files_stmt)
                log.info(
                    'Bulk deletion of associated files complete for '
                    'consultation IDs: %s',
                    ', '.join(map(str, ids_to_delete)))
                # Perform bulk delete
                bulk_delete_stmt = delete(Consultation).where(
                    Consultation.id.in_(ids_to_delete)
                )
                session.execute(bulk_delete_stmt)
                log.info(
                    'Bulk deletion complete. Removed consultations '
                    'with IDs: %s',
                    ', '.join(map(str, ids_to_delete)),
                )
                session.flush()
                return ids_to_delete
            return []


@click.command()
@click.argument('config_uri')
@click.option(
    '--days',
    default=30,
    help='Number of days after which to delete soft-deleted consultations'
)
def hard_delete(config_uri: str, days: int) -> None:
    """
    Hard delete consultation chains where the latest version is soft-deleted
    and older than the specified number of days.
    """
    env = bootstrap(config_uri)
    settings = get_appsettings(config_uri)
    engine = get_engine(settings)
    Base.metadata.create_all(engine)

    with env['request'].tm:
        session = env['request'].dbsession
        deleted_ids = delete_old_consultation_chains(session, days)

        if deleted_ids:
            print(f"Deleted {len(deleted_ids)} consultations:")
            for id in deleted_ids:
                print(f"  - Consultation ID: {id}")
        else:
            print("No consultations were deleted.")


if __name__ == '__main__':
    hard_delete()
