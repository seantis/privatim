import os
import subprocess
import sys
import configparser
from urllib.parse import urlparse

import click

DEFAULT_SSH_USER = os.environ.get('USER', 'user')
REMOTE_DB_NAME = 'privatim'  # DB name on the remote server
REMOTE_DUMP_PATH = '/tmp/privatim.sql'  # Path for SQL dump on remote server
LOCAL_DUMP_PATH = (
    '/tmp/privatim_local.sql'  # Path for SQL dump on local machine
)
LOCAL_TARGET_DB_NAME = 'privatim_prod'  # DB name for local restoration
LOCAL_DB_USER = 'dev'  # Local PostgreSQL user for restoration and grants

POSTGRES_PASSWORD = 'postgres'  # Default password for the local postgres user
# Path template for remote files, server name will be prepended by rsync/scp
REMOTE_FILES_DIR = '/var/lib/privatim/files/'
# Path template for local files, {user} will be replaced by --local-user
LOCAL_FILES_DIR_TEMPLATE = '/home/{user}/privatim/files/'

# Config file for local SQLAlchemy URL
DEV_INI_PATH = 'development.ini'
DEV_INI_EXAMPLE_PATH = 'development.ini.example'


def run_command(
    cmd_list: list[str],
    check: bool = True,
    dry_run: bool = False,
    env: dict[str, str] | None = None,
    **kwargs: object,
) -> subprocess.CompletedProcess[bytes] | subprocess.CompletedProcess[str]:
    """Helper to run a command, print its execution, and handle errors."""
    cmd_str = ' '.join(cmd_list)
    click.echo(click.style(f'Executing: {cmd_str}', fg='yellow'))
    if dry_run:
        click.echo(click.style('Dry run, command not executed.', fg='cyan'))
        return subprocess.CompletedProcess(cmd_list, 0, stdout=b'', stderr=b'')

    try:
        process = subprocess.run(
            cmd_list, check=check, env=env, **kwargs  # type: ignore
        )
        return process
    except subprocess.CalledProcessError as e:
        click.echo(click.style(f'Error executing: {cmd_str}\n{e}', fg='red'))
        if e.stdout:
            out = (
                e.stdout.decode(errors='replace')
                if isinstance(e.stdout, bytes)
                else e.stdout
            )
            click.echo(click.style(f'STDOUT:\n{out}', fg='red'))
        if e.stderr:
            err = (
                e.stderr.decode(errors='replace')
                if isinstance(e.stderr, bytes)
                else e.stderr
            )
            click.echo(click.style(f'STDERR:\n{err}', fg='red'))
        sys.exit(1)
    except FileNotFoundError:
        click.echo(
            click.style(
                f"Error: Command '{cmd_list[0]}' not found. Is it in PATH?",
                fg='red',
            )
        )
        sys.exit(1)


def check_server_known_host(
    server: str, ssh_user: str, dry_run: bool
) -> None:
    """The main script assumes passwordless ssh. This checks if we have."""
    if dry_run:
        click.echo(click.style(
            f'Dry run: Skipping known_hosts check for {server}.',
                   fg='cyan'))
        return
    try:
        process = subprocess.run(
            ['ssh-keygen', '-F', server],
            check=False,  # Handle non-zero exit code manually
            capture_output=True,
            text=True,
        )
        if process.returncode == 0:
            return
        else:
            click.echo(
                click.style(
                    f"Host '{server}' not in SSH known_hosts. Please run:\n"
                    f"  ssh {ssh_user}@{server}\n"
                    f"Then re-run this script.",
                    fg='red',
                )
            )
            sys.exit(1)
    except FileNotFoundError:
        sys.exit(1)

@click.command(name='privatim_transfer')
@click.option(
    '--server',
    required=True,
    help='Remote server hostname or IP address.',
)
@click.option(
    '--dry-run',
    is_flag=True,
    help="Show commands that would be run, but don't execute them.",
)
@click.option(
    '--no-confirm',
    is_flag=True,
    help='Do not ask for confirmation before destructive operations.',
)
@click.option(
    '--no-filestorage',
    is_flag=True,
    help='Skip syncing the filestorage (rsync step).',
)
def main(
    server: str, dry_run: bool, no_confirm: bool, no_filestorage: bool
) -> None:
    """
    Transfers database and files from a remote server:

    privatim_transfer --server helios.seantis.ch
    """

    ssh_user = DEFAULT_SSH_USER
    local_user = DEFAULT_SSH_USER

    if dry_run:
        click.echo(click.style('--- DRY RUN MODE ---', fg='cyan', bold=True))

    # Check if server is in known_hosts before proceeding
    check_server_known_host(server, ssh_user, dry_run)

    selected_server = server

    if not no_filestorage:
        local_files_target_dir = LOCAL_FILES_DIR_TEMPLATE.format(
            user=local_user
        )
        if not dry_run:
            os.makedirs(local_files_target_dir, exist_ok=True)
        else:
            msg = f'Dry run: Would ensure directory exists: {local_files_target_dir}'
            click.echo(click.style(msg, fg='cyan'))

    click.echo(f"\n--- 1. Dumping remote DB on {selected_server} ---")
    dump_cmd_str = (
        f'sudo -i -u postgres pg_dump {REMOTE_DB_NAME} '
        f'--no-owner --no-privileges --no-sync --quote-all-identifiers '
        f'> {REMOTE_DUMP_PATH}'
    )
    run_command(
        ['ssh', f'{ssh_user}@{selected_server}', dump_cmd_str], dry_run=dry_run
    )

    click.echo('\n--- 2. Transferring SQL dump to local machine ---')
    scp_cmd = [
        'scp',
        f'{ssh_user}@{selected_server}:{REMOTE_DUMP_PATH}',
        LOCAL_DUMP_PATH,
    ]
    run_command(scp_cmd, dry_run=dry_run)

    click.echo(
        f'\n--- 3. Setting up local database {LOCAL_TARGET_DB_NAME} ---'
    )
    if not dry_run and not no_confirm:
        if not click.confirm(
            f'Proceed with dropping local database "{LOCAL_TARGET_DB_NAME}"?',
            default=False,
            abort=True,
        ):
            return

    db_ops_env = os.environ.copy()  # For sudo, PG* vars might be reset
    db_ops_env['PGPASSWORD'] = POSTGRES_PASSWORD
    run_command(
        [
            'sudo',
            '-u',
            'postgres',
            'psql',
            '-c',
            f'DROP DATABASE IF EXISTS {LOCAL_TARGET_DB_NAME};',
        ],
        dry_run=dry_run,
        env=db_ops_env,
    )
    run_command(
        [
            'sudo',
            '-u',
            'postgres',
            'psql',
            '-c',
            f'CREATE DATABASE {LOCAL_TARGET_DB_NAME};',
        ],
        dry_run=dry_run,
        env=db_ops_env,
    )
    run_command(
        [
            'sudo',
            '-u',
            'postgres',
            'psql',
            '-c',
            f'GRANT ALL PRIVILEGES ON DATABASE {LOCAL_TARGET_DB_NAME} TO {LOCAL_DB_USER};',  # noqa: E501
        ],
        dry_run=dry_run,
        env=db_ops_env,
    )

    click.echo('\n--- 4. Restoring local database ---')
    restore_cmd = [
        'psql',
        '-U',
        LOCAL_DB_USER,
        '-h',
        'localhost',
        '-d',
        LOCAL_TARGET_DB_NAME,
        '-f',
        LOCAL_DUMP_PATH,
    ]
    run_command(restore_cmd, dry_run=dry_run)

    if not no_filestorage:
        click.echo('\n--- 5. Syncing files via rsync ---')
        local_files_target_dir = LOCAL_FILES_DIR_TEMPLATE.format(
            user=local_user
        )  # Define it here if not defined earlier
        if not dry_run and not no_confirm and not click.confirm(
            f'Proceed with syncing files to "{local_files_target_dir}"?',
            default=False,
        ):
            click.echo(
                click.style('Skipping file sync as requested.', fg='yellow')
            )
        else:
            remote_rsync_source = (
                f'{ssh_user}@{selected_server}:{REMOTE_FILES_DIR}'
            )
            # Ensure local_files_target_dir ends with a slash for rsync
            local_rsync_target = os.path.join(local_files_target_dir, '')
            rsync_cmd = [
                'rsync',
                '-avz',
                '-e',
                'ssh',
                remote_rsync_source,
                local_rsync_target,
            ]
            run_command(rsync_cmd, dry_run=dry_run)
    else:
        click.echo(
            click.style(
                '\n--- Skipping file sync (--no-filestorage) ---', fg='yellow'
            )
        )

    click.echo('\n--- 6. Cleaning up temporary local SQL dump ---')
    if not dry_run:
        try:
            os.remove(LOCAL_DUMP_PATH)
            click.echo(f'Removed {LOCAL_DUMP_PATH}')
        except OSError as e:
            click.echo(
                click.style(
                    f'Warning: Could not remove {LOCAL_DUMP_PATH}: {e}',
                    fg='yellow',
                )
            )
    else:
        click.echo(
            click.style(f'Dry run: Would remove {LOCAL_DUMP_PATH}', fg='cyan')
        )

    click.echo('\n--- 7. Adding default admin user ---')
    add_user_cmd = [
        'venv/bin/add_user',
        DEV_INI_PATH,
        '--email',
        'admin@example.org',
        '--password',
        'test',
        '--first_name',
        local_user,
        '--last_name',
        'K.',
    ]
    run_command(add_user_cmd, dry_run=dry_run)

    # Check local sqlalchemy.url
    config_file_to_check = ''
    if os.path.exists(DEV_INI_PATH):
        config_file_to_check = DEV_INI_PATH
    else:
        click.echo(
            click.style(
                "\n--- WARNING: Can't find development.ini ---",
                fg='yellow',
                bold=True,
            )
        )

    # basic sanity to checks to make sure the db name is correct
    if config_file_to_check:
        config = configparser.ConfigParser()
        try:
            config.read(config_file_to_check)
            if 'app:main' in config and 'sqlalchemy.url' in config['app:main']:
                sqlalchemy_url = config['app:main']['sqlalchemy.url']
                parsed_url = urlparse(sqlalchemy_url)
                current_db_name = parsed_url.path.lstrip('/')
                if current_db_name != LOCAL_TARGET_DB_NAME:
                    click.echo(
                        click.style(
                            "\n--- WARNING: Database Name Mismatch ---",
                            fg='yellow',
                            bold=True,
                        )
                    )
                    click.echo(
                        f"The database '{LOCAL_TARGET_DB_NAME}' was created, "
                        f"but your "
                        f"'{config_file_to_check}' is configured to use "
                        f"'{current_db_name}'."
                    )
                    click.echo(
                        f"Please update 'sqlalchemy.url' in "
                        f"'{config_file_to_check}' to " f"point to "
                        f"'{LOCAL_TARGET_DB_NAME}'."
                    )
        except Exception as e:
            click.echo(
                click.style(
                    f"Could not parse '{config_file_to_check}': {e}",
                    fg='yellow',
                )
            )

    if dry_run:
        click.echo(
            click.style('--- DRY RUN MODE END ---', fg='cyan', bold=True)
        )
    else:
        click.echo(
            click.style(
                '\n--- Transfer process completed. ---', fg='green', bold=True
            )
        )
