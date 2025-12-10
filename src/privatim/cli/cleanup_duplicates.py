import click
from pyramid.paster import bootstrap, get_appsettings
from sqlalchemy import delete, text
import transaction
from privatim.models.association_tables import AgendaItemStatePreference
from privatim.orm import get_engine
from privatim.orm.meta import Base


@click.command()
@click.option(
    '--dry-run',
    is_flag=True,
    help='Find and list duplicates without deleting them.'
)
@click.argument('config_uri')
def cleanup_duplicate_agenda_preferences(
    config_uri: str, dry_run: bool
) -> None:
    """
    Finds and removes duplicate agenda item state preferences.
    """
    env = bootstrap(config_uri)
    settings = get_appsettings(config_uri)
    engine = get_engine(settings)
    Base.metadata.create_all(engine)

    with env['request'].tm:
        session = env['request'].dbsession

        print('Searching for duplicate agenda item state preferences...')

        # Find duplicates
        duplicates = session.execute(text(
            """
            SELECT user_id, agenda_item_id, COUNT(id)
            FROM agenda_item_state_preferences
            GROUP BY user_id, agenda_item_id
            HAVING COUNT(id) > 1
            """
        )).fetchall()

        if not duplicates:
            print('No duplicates found.')
            return

        print(f"Found {len(duplicates)} sets of duplicates.")

        # For each duplicate set, find the IDs to delete
        ids_to_delete = []
        for user_id, agenda_item_id, count in duplicates:
            print(
                f"Found {count} entries for user {user_id} and "
                f"agenda item {agenda_item_id}."
            )
            # Get all IDs for this pair, ordered by ID
            preferences = (
                session.query(AgendaItemStatePreference.id)
                .filter_by(user_id=user_id, agenda_item_id=agenda_item_id)
                .order_by(AgendaItemStatePreference.id)
                .all()
            )

            # Keep the first one, mark the rest for deletion
            ids_to_delete.extend([p.id for p in preferences[1:]])

        if not ids_to_delete:
            print('No excess entries to delete.')
            return

        if dry_run:
            print("\n--- DRY RUN ---")
            print(f"{len(ids_to_delete)} duplicate entries would be deleted:")
            for item_id in ids_to_delete:
                print(f"  - ID: {item_id}")
            print(
                "\nTo delete these entries, run the command without the "
                "--dry-run flag."
            )
            return

        print(f"Deleting {len(ids_to_delete)} duplicate entries...")

        # Delete the duplicates
        session.execute(
            delete(AgendaItemStatePreference).where(
                AgendaItemStatePreference.id.in_(ids_to_delete)
            )
        )

        transaction.commit()
        print('Cleanup complete.')
