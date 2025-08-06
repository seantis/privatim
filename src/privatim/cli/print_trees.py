import click
from pyramid.paster import bootstrap
from pyramid.paster import get_appsettings
from sqlalchemy import select, text
from pyramid.request import Request

from sqlalchemy.orm import joinedload
from privatim.models import Consultation
from privatim.orm import get_engine, Base


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from privatim.orm.session import FilteredSession


def print_consultation_tree(
    consultation: Consultation, level: int = 0
) -> None:
    """Print a single consultation and its version history recursively."""
    indent = '  ' * level
    version_status = 'LATEST' if consultation.is_latest() else 'OLD'
    click.echo(
        f'{indent}├── {consultation.title} ({version_status}) '
        f'[ID: {consultation.id}]'
    )

    if consultation.previous_version:
        print_consultation_tree(consultation.previous_version, level + 1)


def print_latest_consultations_with_files(
    dbsession: 'FilteredSession', request: Request
) -> None:
    """Print all latest consultations with their attached files."""
    query = select(Consultation).where(
        Consultation.is_latest_version == 1
    ).order_by(Consultation.title)

    latest_consultations = dbsession.execute(query).scalars().all()

    if not latest_consultations:
        click.echo('No latest consultations found.')
        return

    click.echo('\nLatest Consultations with Files:\n')

    for i, consultation in enumerate(latest_consultations, 1):
        url = request.route_url('consultation', id=consultation.id)
        click.echo(f'{i}. {consultation.title} [ID: {consultation.id}]')
        click.echo(f'   URL: {url}')
        click.echo(f'   Status: {consultation.status}')

        if consultation.files:
            for j, file in enumerate(consultation.files, 1):
                click.echo(f'   └── File {j}: {file.name}')
        else:
            click.echo('   └── No files attached')

        click.echo('')


@click.group()
def cli() -> None:
    """Consultation tree management commands."""
    pass


@cli.command('trees')
@click.argument('config_uri')
@click.option(
    '--title-filter',
    help='Only show consultations containing this text in the title',
)
@click.option(
    '--id',
    help='Print consultation tree by id',
)
def print_trees(
    config_uri: str,
    title_filter: str | None,
    id: str | None) -> None:
    """
    Print all consultation version trees.

    Shows the version history chains of all consultations, with optional title
    filtering.

    for example:
    print_trees trees --id "some-id" development.ini
    """
    env = bootstrap(config_uri)
    settings = get_appsettings(config_uri)
    engine = get_engine(settings)
    Base.metadata.create_all(engine)

    with env['request'].tm:
        dbsession = env['request'].dbsession

        root_consultations: list[Consultation]

        with dbsession.no_consultation_filter():
            if id:
                target_consultation = dbsession.get(Consultation, id)
                if not target_consultation:
                    click.echo(f"Consultation with ID {id} not found.")
                    return

                # Find the root of the tree containing this consultation.
                # The root is the one where replaced_consultation_id IS NULL.
                # replaced_consultation_id stores the ID of the *previous*
                # version.
                query_str = """
                    WITH RECURSIVE ancestors AS (
                        SELECT id, replaced_consultation_id
                        FROM consultations
                        WHERE id = :target_id
                        UNION ALL
                        SELECT c.id, c.replaced_consultation_id
                        FROM consultations c
                        JOIN ancestors a ON c.id = a.replaced_consultation_id
                    )
                    SELECT id
                    FROM ancestors
                    WHERE replaced_consultation_id IS NULL
                    LIMIT 1;
                """
                root_id_result = dbsession.execute(
                    text(query_str), {'target_id': id}
                ).scalar_one_or_none()

                if not root_id_result:
                    click.echo(
                        f"Could not determine the root for consultation ID {id}."
                        " It might be an orphaned record or part of a cycle."
                    )
                    return

                root_consultation = dbsession.get(Consultation, root_id_result)
                if not root_consultation:
                    # This should ideally not happen if root_id_result was valid
                    click.echo(
                        f"Found root ID {root_id_result} but failed to fetch "
                        "the consultation object."
                    )
                    return
                root_consultations = [root_consultation]
            else:
                # Get all root consultations (those not previous versions)
                query = select(Consultation).where(
                    Consultation.replaced_consultation_id.is_(None)
                )
                if title_filter:
                    query = query.where(
                        Consultation.title.ilike(f'%{title_filter}%')
                    )
                root_consultations = dbsession.execute(query).scalars().all()


            if not root_consultations:
                click.echo('No consultations found.')
                return

            click.echo('\nConsultation Version Trees:\n')

            # Sort by title for consistent output
            root_consultations.sort(key=lambda x: x.title)

            for i, consultation in enumerate(root_consultations, 1):
                click.echo(f'\nTree {i}:')
                print_consultation_tree(consultation)


@cli.command('validate')
@click.argument('config_uri')
def validate_trees(config_uri: str) -> None:
    """
    Validate consultation version trees.

    Checks each consultation tree to ensure that exactly one version in each
    chain is marked as `is_latest_version = TRUE`.

    print_trees validate development.ini
    """
    env = bootstrap(config_uri)
    settings = get_appsettings(config_uri)
    engine = get_engine(settings)
    Base.metadata.create_all(engine)
    closer = env['closer']

    with env['request'].tm:
        dbsession: 'FilteredSession' = env['request'].dbsession
        all_trees_valid = True
        error_messages: list[str] = []

        with dbsession.no_consultation_filter():
            # Get all root consultations (those that are not previous versions)
            root_query = select(Consultation).where(
                Consultation.replaced_consultation_id.is_(None)
            )
            root_consultations = dbsession.execute(
                root_query.order_by(Consultation.title)
            ).scalars().all()

            if not root_consultations:
                click.echo('No consultation trees found to validate.')
                closer()
                return

            click.echo(f'Found {len(root_consultations)} consultation tree(s) to validate.')

            sql_query = text("""
                WITH RECURSIVE full_chain AS (
                    SELECT id, replaced_consultation_id, is_latest_version, title
                    FROM consultations
                    WHERE id = :root_id
                UNION ALL
                    SELECT c.id, c.replaced_consultation_id, c.is_latest_version, c.title
                    FROM consultations c
                    JOIN full_chain fc ON c.replaced_consultation_id = fc.id
                )
                SELECT COUNT(*)
                FROM full_chain
                WHERE is_latest_version = 1;
            """)

            for root in root_consultations:
                count_result = dbsession.execute(
                    sql_query, {'root_id': root.id}
                ).scalar_one_or_none()

                if count_result != 1:
                    # This error is about the *number* of latest flags in the chain
                    all_trees_valid = False
                    msg = (f'VALIDATION ERROR (Count): Tree for root "{root.title}" (ID: {root.id})'
                           f' has {count_result} version(s) marked as latest (is_latest_version=1). Expected exactly 1.')
                    error_messages.append(msg)
                    click.echo(click.style(msg, fg='red'))

                # Detailed chain structure validation using Python objects
                current_node: Consultation | None = root
                visited_in_current_chain_check: set[str] = set()

                while current_node:
                    if current_node.id in visited_in_current_chain_check:
                        all_trees_valid = False
                        msg = (
                            f'VALIDATION ERROR (Cycle): Cycle detected in chain starting from root "{root.title}" (ID: {root.id}). '
                            f'Node "{current_node.title}" (ID: {current_node.id}) encountered again.'
                        )
                        error_messages.append(msg)
                        click.echo(click.style(msg, fg='red'))
                        break  # Break from while loop for this chain
                    visited_in_current_chain_check.add(current_node.id)

                    is_marked_latest = (current_node.is_latest_version == 1)
                    # Check relationship from current_node to its *next* version
                    has_next_version = (current_node.replaced_by is not None)

                    if is_marked_latest:
                        if has_next_version:
                            all_trees_valid = False
                            next_node_id_str = current_node.replaced_by.id if current_node.replaced_by else "UNKNOWN_ID"
                            msg = (
                                f'VALIDATION ERROR (Link): Node "{current_node.title}" (ID: {current_node.id}) in tree of root "{root.title}" '
                                f'is marked LATEST (is_latest_version=1) but HAS a "replaced_by" link '
                                f'to version ID "{next_node_id_str}". A latest version should not be replaced.'
                            )
                            error_messages.append(msg)
                            click.echo(click.style(msg, fg='red'))
                    else:  # Not marked latest (is_latest_version != 1)
                        if not has_next_version:
                            # This is the condition that would cause the AssertionError in get_latest_version
                            all_trees_valid = False
                            msg = (
                                f'VALIDATION ERROR (Link): Node "{current_node.title}" (ID: {current_node.id}) in tree of root "{root.title}" '
                                f'is marked NOT LATEST (is_latest_version={current_node.is_latest_version}) '
                                f'but has NO "replaced_by" link. It is a dead-end.'
                            )
                            error_messages.append(msg)
                            click.echo(click.style(msg, fg='red'))
                            # This chain is broken here for get_latest_version logic.
                            break # Stop traversing this broken chain for link checks.

                    current_node = current_node.replaced_by

        if all_trees_valid:
            click.echo(click.style('All consultation trees are valid.', fg='green'))
        else:
            click.echo(click.style(
                f'\nValidation finished. {len(error_messages)} tree(s) have issues.', fg='red'
            ))
        closer()

@cli.command('latest-with-files')
@click.argument('config_uri')
def print_latest_with_files(config_uri: str) -> None:
    """
    Print all latest consultations with their attached files.

    Shows only the latest version of each consultation and lists their
    attached files.
    """
    env = bootstrap(config_uri)
    settings = get_appsettings(config_uri)
    registry = env['registry']
    engine = get_engine(settings)
    Base.metadata.create_all(engine)
    closer = env['closer']

    with env['request'].tm:
        dbsession = env['request'].dbsession

        # This is the crucial part, if we don't have this request_route url
        # will not respect the used path
        host = settings.get('pyramid.url_host', '127.0.0.1')
        port = settings.get('pyramid.url_port', '6543')
        scheme = settings.get('pyramid.url_scheme', 'http')
        http_host = f"{host}:{port}" if port and port != '80' else host
        server_port = str(port) if port else '80'
        environ = {
            'wsgi.url_scheme': scheme,
            'HTTP_HOST': http_host,
            'SERVER_NAME': host,
            'SERVER_PORT': server_port,
            # Add other minimal required environ keys if necessary
            'PATH_INFO': '/',
            'REQUEST_METHOD': 'GET',
        }

        request = Request(environ)
        # IMPORTANT: Associate the request with the application registry
        # This allows route_url to find the route definitions
        request.registry = registry

        print_latest_consultations_with_files(dbsession, request)
        closer()


@cli.command('temp-delete-consultations-by-keyword')
@click.argument('config_uri')
@click.option(
    '--keyword',
    default='Engagement',
    help='Case-insensitive keyword to find in consultation titles for deletion.',
    show_default=True
)
def temp_delete_consultations_by_keyword(
    config_uri: str, keyword: str
) -> None:
    """
    Temporarily delete all consultations with a specific keyword.

    This command ignores the standard consultation filters and carefully
    unlinks versions before deleting to prevent unintended cascade deletions.
    Searches for consultations with the specified keyword (case-insensitive)
    in title.
    """
    env = bootstrap(config_uri)
    closer = env['closer']

    try:
        with env['request'].tm:
            dbsession: 'FilteredSession' = env['request'].dbsession

            with dbsession.no_consultation_filter():
                consultation_query = select(Consultation).options(
                    joinedload(Consultation.creator),
                    joinedload(Consultation.previous_version),
                ).where(
                    Consultation.title.ilike(f'%{keyword}%')
                )
                consultations_to_delete = dbsession.execute(
                    consultation_query
                ).scalars().all()

                if not consultations_to_delete:
                    click.echo(
                        f"No consultations with '{keyword}' in title found."
                    )
                    return

                click.echo(
                    f"Found {len(consultations_to_delete)} consultations "
                    "to delete:"
                )
                for cons_info in consultations_to_delete:
                    click.echo(f"  - {cons_info.title} (ID: {cons_info.id})")

                if not click.confirm(
                    'Do you want to proceed with deleting these '
                    'consultations?',
                    abort=True
                ):
                    # This path is actually unreachable due to abort=True
                    # but kept for clarity if abort=True is removed.
                    return # pragma: no cover

                for cons in consultations_to_delete:
                    cons_id = cons.id
                    click.echo(
                        f"Processing consultation: {cons.title} "
                        f"(ID: {cons_id})"
                    )

                    update_sql = text(
                        "UPDATE consultations SET replaced_consultation_id = "
                        "NULL WHERE replaced_consultation_id = :target_id"
                    )
                    result_update = dbsession.execute(
                        update_sql, {'target_id': cons_id}
                    )
                    click.echo(
                        "  Unlinked subsequent versions from "
                        f"{cons_id}. Rows affected: {result_update.rowcount}"
                    )

                    delete_sql = text(
                        "DELETE FROM consultations WHERE id = :target_id"
                    )
                    result_delete = dbsession.execute(
                        delete_sql, {'target_id': cons_id}
                    )
                    click.echo(
                        f"  Deleted consultation {cons_id}. "
                        f"Rows affected: {result_delete.rowcount}"
                    )

                    commit_sql = text(
                        "COMMIT;"
                    )
                    result_delete = dbsession.execute(
                        commit_sql , {'target_id': cons_id}
                    )
                click.echo(click.style(
                    "Deletion process complete.", fg='green'
                ))
    finally:
        closer()


def main() -> None:
    """Entry point for the console script."""
    cli()


if __name__ == '__main__':
    cli()
@cli.command('single')
@click.argument('config_uri')
@click.argument('consultation_id')
def print_single_consultation(config_uri: str, consultation_id: str) -> None:
    """
    Print a single consultation tree by ID.

    Shows the version history chain for the specified consultation.

    Usage: venv/bin/print_trees single development.ini <consultation-id>
    """
    env = bootstrap(config_uri)
    settings = get_appsettings(config_uri)
    engine = get_engine(settings)
    Base.metadata.create_all(engine)
    closer = env['closer']

    with env['request'].tm:
        dbsession = env['request'].dbsession

        with dbsession.no_consultation_filter():
            consultation = dbsession.get(Consultation, consultation_id)
            if not consultation:
                click.echo(f'Consultation with ID {consultation_id} not found.')
                closer()
                return

            # Find the root of this consultation's tree
            root = consultation
            while root.previous_version:
                root = root.previous_version

            click.echo(f'\nConsultation Tree for ID {consultation_id}:\n')
            print_consultation_tree(root)

    closer()

