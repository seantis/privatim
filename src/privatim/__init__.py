from __future__ import annotations
from functools import partial
from fanstatic import Fanstatic
from psycopg2 import ProgrammingError

from pyramid.events import BeforeRender
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.exc import SQLAlchemyError

from privatim import helpers
from pyramid.config import Configurator
from pyramid_beaker import session_factory_from_settings
from sqlalchemy import Column, ForeignKey, String, TIMESTAMP, func, Computed, \
    VARCHAR, text, Boolean
from email.headerregistry import Address

from privatim.mail import PostmarkMailer
from privatim.models.comment import COMMENT_DELETED_MSG
from privatim.orm.uuid_type import UUIDStr as UUIDStrType

from pyramid.settings import asbool
from privatim.file.setup import setup_filestorage
from privatim.flash import MessageQueue
from privatim.i18n import LocaleNegotiator
from privatim.route_factories.root_factory import root_factory
from privatim.security import authenticated_user
from privatim.security_policy import SessionSecurityPolicy
from privatim.sms.sms_gateway import ASPSMSGateway


from typing import Any, TYPE_CHECKING
from typing import Any as Incomplete
from privatim.utils import fix_agenda_item_positions
from subscribers import register_subscribers

if TYPE_CHECKING:
    from collections.abc import Iterable
    from privatim.controls.controls import Button
    from _typeshed.wsgi import WSGIApplication
    from privatim.cli.upgrade import UpgradeContext
    from pyramid.interfaces import IRequest


def includeme(config: Configurator) -> None:

    settings = config.registry.settings
    default_sender = settings.get(
        'mail.default_sender',
        'no-reply@privatim-test.seantis.ch'
    )
    token = settings.get('mail.postmark_token', 'POSTMARK_API_TEST')
    stream = settings.get('mail.postmark_stream', 'outbound')
    blackhole = asbool(settings.get('mail.postmark_blackhole', False))
    config.registry.registerUtility(PostmarkMailer(
        Address(addr_spec=default_sender),
        token,
        stream,
        blackhole=blackhole
    ))
    smsdir = settings.get('sms.queue_path', '')
    config.registry.registerUtility(ASPSMSGateway(smsdir))

    config.include('pyramid_beaker')
    config.include('pyramid_chameleon')
    config.include('pyramid_layout')
    config.include('privatim.layouts')
    config.include('privatim.models')
    config.include('privatim.views')

    config.set_locale_negotiator(LocaleNegotiator())
    config.add_translation_dirs('privatim:locale')
    # wtforms 3.0 ships with its own translations
    config.add_translation_dirs('wtforms:locale')

    register_subscribers(config)

    session_factory = session_factory_from_settings(settings)
    config.set_session_factory(session_factory)

    security_policy = SessionSecurityPolicy(timeout=28800)
    config.set_security_policy(security_policy)

    config.set_default_permission('view')
    config.set_default_csrf_options(require_csrf=True)

    config.add_request_method(authenticated_user, 'user', property=True)

    def profile_pic(request: 'IRequest') -> str:
        user = request.user
        if not user:
            return ''
        return request.route_url('download_file', id=user.picture.id)

    # todo: this can probably be cached:
    config.add_request_method(profile_pic, 'profile_pic', property=True)

    config.add_request_method(MessageQueue, 'messages', reify=True)

    rev = settings.get('git_revision', '')
    config.add_request_method(lambda r: rev, 'git_revision')

    def add_action_menu_entries(
        request: 'IRequest',
        entries: Iterable['Button'],
    ) -> None:
        """
        Action menus are a list of buttons that are displayed in the top right.
        The attribute is stored on the request (dynamically).
        """
        if not hasattr(request, 'action_menu_entries'):
            request.action_menu_entries = []
        request.action_menu_entries.extend(entries)

    config.add_request_method(
        lambda request: partial(add_action_menu_entries, request),
        'add_action_menu_entries',
        reify=True,
    )


def add_renderer_globals(event: Incomplete) -> None:
    """ Makes the helpers module available in all templates.
    For example, you can access Markup via 'h':

    <h4 tal:content="h.Markup(activity.title[:100])>

    """
    event['h'] = helpers


def main(
    global_config: Any, **settings: Any
) -> 'WSGIApplication':  # pragma: no cover

    sentry_dsn = settings.get('sentry_dsn')
    sentry_environment = settings.get('sentry_environment', 'development')
    if sentry_dsn:
        import sentry_sdk
        from sentry_sdk.integrations.pyramid import PyramidIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=sentry_environment,
            integrations=[PyramidIntegration(), SqlalchemyIntegration()],
            traces_sample_rate=1.0,
            profiles_sample_rate=0.25,
        )

    setup_filestorage(settings)

    with Configurator(settings=settings, root_factory=root_factory) as config:
        includeme(config)
        config.add_subscriber(add_renderer_globals, BeforeRender)

    app = config.make_wsgi_app()
    return Fanstatic(app, versioning=True)


def fix_user_constraints_to_work_with_hard_delete(
        context: 'UpgradeContext'
) -> None:
    op = context.operations
    conn = op.get_bind()

    fk_constraints = [
        ('consultations', 'creator_id', 'fk_consultations_creator_id_users'),
        ('consultations', 'editor_id', 'fk_consultations_editor_id_users'),
        ('meetings', 'creator_id', 'fk_meetings_creator_id_users'),
        #  Add all other foreign key constraints here
    ]

    for table, column, constraint in fk_constraints:
        # Check if constraint exists
        try:
            exists = conn.execute(text(
                f"SELECT 1 FROM information_schema.table_constraints "
                f"WHERE constraint_name = '{constraint}'"  # nosec[B608]
            )).scalar()
        except SQLAlchemyError:
            exists = False

        if exists:
            try:
                op.drop_constraint(constraint, table, type_='foreignkey')
            except (ProgrammingError, SQLAlchemyError) as e:
                print(
                    f"Error dropping constraint {constraint} on table {table}:"
                    f" {e!s}"
                )
        else:
            print(
                f"Constraint {constraint} on table {table} doesn't exist, "
                f"skipping drop"
            )

        # Recreate the constraint with ON DELETE SET NULL
        try:
            op.create_foreign_key(
                constraint,
                table,
                'users',
                [column],
                ['id'],
                ondelete='SET NULL',
            )
        except SQLAlchemyError as e:
            print(
                f"Error creating constraint {constraint} on table {table}: "
                f"{e!s}")


def upgrade(context: 'UpgradeContext') -> None:
    context.add_column(
        'meetings',
        Column(
            'updated',
            TIMESTAMP(timezone=False),
            server_default=func.now()
        )
    )

    context.alter_column(
        'comments',
        'modified',
        new_column_name='updated'
    )

    # drop unused Statements column
    context.drop_column('user', 'statements')
    context.drop_table('statements')

    if not context.has_column('meetings', 'creator_id'):
        context.add_column(
            'meetings',
            Column(
                'creator_id',
                UUIDStrType,
                ForeignKey('users.id', ondelete='SET NULL'),
                nullable=True,
            ),
        )
    if context.has_table('meetings_users_association'):
        # Migrate data from meetings_users to meetings_users_attendance
        # this also stores the  field if attended
        context.operations.execute(
            """
            INSERT INTO meetings_users_attendance (meeting_id, user_id, status)
            SELECT meeting_id, user_id, 'INVITED'::attendancestatus
            FROM meetings_users_association
            """
        )
        context.drop_table('meetings_users_association')

    context.add_column(
        'users',
        Column(
            'mobile_number',
            String(length=128),
            nullable=True
        )
    )

    # New changes for consultations and files

    # 1. Drop the association table
    context.drop_table('searchable_files_for_consultations_files')

    # 2. Add consultation_id to searchable_files
    context.add_column(
        'searchable_files',
        Column(
            'consultation_id',
            UUIDStrType,
            ForeignKey('consultations.id'),
            nullable=True,
        ),
    )

    # 3. drop previous
    context.drop_column('consultations', 'searchable_text_de_CH')

    context.add_column(
        'searchable_files',
        Column(
            'searchable_text_de_CH',
            TSVECTOR,
            Computed(
                "to_tsvector('german', COALESCE(extract, ''))",
                persisted=True
            ),
            nullable=True,
        ),

    )

    if not context.index_exists(
        'searchable_files', 'idx_searchable_files_searchable_text_de_CH'
    ):
        # this needs to be added in the second run
        context.operations.create_index(
            'idx_searchable_files_searchable_text_de_CH',
            'searchable_files',
            ['searchable_text_de_CH'],
            postgresql_using='gin',
        )

    # Drop all existing comments and related tables
    context.drop_table('comments_for_consultations_comments')
    context.drop_table('comments_for_meetings_comments')

    # For simplicity, first drop it, then re-create the comments table.
    # Base.metadata.create_all() should do the job.
    # context.drop_table('comments')

    context.add_column(
        'comments',
        Column('target_id', UUIDStrType, nullable=False)
    )
    context.add_column(
        'comments',
        Column('target_type', String(50), nullable=False)
    )

    context.add_column(
        'users',
        Column('locale', String(32), nullable=True)
    )

    # Make name of user not nullable anymore
    # First, update any existing NULL values to an empty string
    context.operations.execute(
        "UPDATE users SET first_name = '' WHERE first_name IS NULL"
    )
    context.operations.execute(
        "UPDATE users SET last_name = '' WHERE last_name IS NULL"
    )

    # Now, alter the columns to be NOT NULL
    context.alter_column(
        'users',
        'first_name',
        existing_type=VARCHAR(length=256),
        nullable=False,
        server_default='',
    )

    context.alter_column(
        'users',
        'last_name',
        existing_type=VARCHAR(length=256),
        nullable=False,
        server_default='',
    )

    fix_user_constraints_to_work_with_hard_delete(context)

    # Add 'deleted' column to 'consultations' table
    context.add_column(
        'consultations',
        Column(
            'deleted',
            Boolean,
            nullable=False,
            server_default='false',
        ),
    )

    # Add 'deleted' column to 'searchable_files' table
    context.add_column(
        'searchable_files',
        Column(
            'deleted',
            Boolean,
            nullable=False,
            server_default='false',
        ),
    )

    if not context.index_exists(
            'consultations', 'ix_consultations_deleted'
    ):
        context.operations.create_index(
            context.operations.f('ix_consultations_deleted'),
            'consultations',
            ['deleted'],
            unique=False,
        )

    if not context.index_exists(
        'searchable_files', 'ix_searchable_files_deleted'
    ):
        context.operations.create_index(
            context.operations.f('ix_searchable_files_deleted'),
            'searchable_files',
            ['deleted'],
            unique=False,
        )

    context.add_column('users', Column('tags', String(255), nullable=True))

    # Drop old columns and tables
    # context.drop_column('consultations', 'status_id')
    # context.drop_table('status')
    # context.drop_table('secondary_tags')

    context.add_column(
        'consultations',
        Column(
            'status', String(256), nullable=False, server_default='Created'
        ),
    )
    context.add_column(
        'consultations',
        Column(
            'secondary_tags',
            postgresql.ARRAY(String(32)),
            nullable=False,
            server_default='{}',
        ),
    )

    context.drop_column('users', 'function')

    # Drop the existing chairman_contact column
    context.drop_column('working_groups', 'chairman_contact')

    # Add the new chairman_id column as a foreign key to users
    context.add_column(
        'working_groups',
        Column(
            'chairman_id',
            UUIDStrType,
            ForeignKey('users.id', ondelete='SET NULL'),
            nullable=True,
        ),
    )

    context.alter_column(
        'users',
        'tags',
        new_column_name='abbrev'
    )
    context.alter_column(
        'users',
        'modified',
        new_column_name='updated'
    )
    context.add_column(
        'users',
        Column(
            'created',
            TIMESTAMP(timezone=False),
            server_default=func.now()
        )
    )

    # Get all available translations of the deleted message
    translated_messages = {str(COMMENT_DELETED_MSG),  # untranslated
                           'Comment deleted by user',  # fallback English
                           '[Kommentar von Benutzer gelöscht]',
                           "[Commentaire supprimé par l'utilisateur]"
                           }
    if context.add_column(
            'comments',
            Column(
                'deleted',
                Boolean,
                nullable=False,
                server_default='false',
            ),
    ):
        # Update existing deleted comments using OR conditions for each
        # translation. Double up single quotes for SQL escaping
        escaped_messages = [msg.replace("'", "''")
                            for msg in translated_messages]
        conditions = " OR ".join(f"content = '{msg}'"
                                 for msg in escaped_messages)
        query = """
        UPDATE comments
        SET deleted = true
        WHERE """ + conditions  # nosec[B608]
        context.session.execute(text(query))

    context.drop_column('consultations', 'updated')

    # --- Migrate SearchableFile parent relationship ---
    print("Migrating SearchableFile parent structure...")
    table_name = 'searchable_files'
    old_parent_id_col = 'parent_id'  # Old column storing the parent ID
    old_parent_type_col = 'parent_type'  # Old column storing parent type
    consultation_fk_col = 'consultation_id'  # New FK for Consultations
    meeting_fk_col = 'meeting_id'  # New FK column for Meetings
    constraint_name = f'chk_{table_name}_one_parent'  # Ensures one FK is set
    consultation_idx = f'ix_{table_name}_{consultation_fk_col}'
    meeting_idx = f'ix_{table_name}_{meeting_fk_col}'

    # Step 1: Add new FK columns (nullable initially) if they don't exist
    consultation_col_exists = context.has_column(
        table_name, consultation_fk_col)
    if not consultation_col_exists:
        print(f"  Adding column {consultation_fk_col} to {table_name}")
        context.add_column(
            table_name,
            Column(
                consultation_fk_col,
                UUIDStrType,
                ForeignKey('consultations.id', ondelete='CASCADE'),
                nullable=True
            )
        )
    else:
        print(f"  Column {consultation_fk_col} already exists in {table_name}")
        # Ensure it's nullable for data migration step if it exists
        context.alter_column(table_name, consultation_fk_col, nullable=True)

    meeting_col_exists = context.has_column(table_name, meeting_fk_col)
    if not meeting_col_exists:
        print(f"  Adding column {meeting_fk_col} to {table_name}")
        context.add_column(
            table_name,
            Column(
                meeting_fk_col,
                UUIDStrType,
                ForeignKey('meetings.id', ondelete='CASCADE'),
                nullable=True
            )
        )
    else:
        print(f"  Column {meeting_fk_col} already exists in {table_name}")
        # Ensure it's nullable for data migration step if it exists
        context.alter_column(table_name, meeting_fk_col, nullable=True)

    # Step 2: Migrate data from old columns to new columns if old columns exist
    old_id_col_exists = context.has_column(table_name, old_parent_id_col)
    old_type_col_exists = context.has_column(table_name, old_parent_type_col)

    if old_id_col_exists and old_type_col_exists:
        print("  Migrating data from old parent columns to new FK columns...")
        # Migrate Consultations
        update_consultations = text(f"""
            UPDATE {table_name}
            SET {consultation_fk_col} = {old_parent_id_col}::uuid
            WHERE {old_parent_type_col} = 'consultations'
            AND {consultation_fk_col} IS NULL -- Only update if not already set
        """)  # nosec[B608]
        context.session.execute(update_consultations)

        # Migrate Meetings (if they were ever supported by old columns)
        update_meetings = text(f"""
            UPDATE {table_name}
            SET {meeting_fk_col} = {old_parent_id_col}::uuid
            WHERE {old_parent_type_col} = 'meetings'
            AND {meeting_fk_col} IS NULL -- Only update if not already set
        """)  # nosec[B608]
        context.session.execute(update_meetings)
        print("  Data migration complete.")
    else:
        print("  Old parent columns not found, skipping data migration.")

    # Step 3: Add Check Constraint if it doesn't exist
    # This ensures exactly one parent FK is set going forward.
    # We add this *after* data migration.
    if not context.has_constraint(table_name, constraint_name, 'CHECK'):
        print(f"  Adding check constraint {constraint_name} to {table_name}")
        try:
            context.operations.create_check_constraint(
                constraint_name=constraint_name,
                table_name=table_name,
                condition=f"num_nonnulls({consultation_fk_col}, "
                f"{meeting_fk_col}) = 1"
            )
            print(f"  Added check constraint {constraint_name}.")
        except Exception as e:
            # It might fail if there's data violating the constraint *after*
            # migration
            print(
                f"  ERROR: Could not add check constraint {constraint_name}. "
                f"Check data in {table_name} - rows must have exactly one "
                f"of {consultation_fk_col} or {meeting_fk_col} set. "
                f"Error: {e}"
            )
            # Depending on policy, you might raise an error here or just warn
    else:
        print(f"  Check constraint {constraint_name} already exists.")

    # Step 4: Add Indexes for new FK columns if they don't exist
    if not context.index_exists(table_name, consultation_idx):
        print(f"  Adding index {consultation_idx} to {table_name}")
        context.operations.create_index(
            consultation_idx, table_name, [consultation_fk_col]
        )
    else:
        print(f"  Index {consultation_idx} already exists.")

    if not context.index_exists(table_name, meeting_idx):
        print(f"  Adding index {meeting_idx} to {table_name}")
        context.operations.create_index(
            meeting_idx, table_name, [meeting_fk_col]
        )
    else:
        print(f"  Index {meeting_idx} already exists.")

    # Step 5: Drop old columns if they exist
    if context.drop_column(table_name, old_parent_id_col):
        print(f"  Dropped old column {old_parent_id_col} from {table_name}.")
    if context.drop_column(table_name, old_parent_type_col):
        print(f"  Dropped old column {old_parent_type_col} from {table_name}.")

    print("Finished migrating SearchableFile parent structure.")
    # --- End of SearchableFile parent migration ---

    fix_agenda_item_positions(context)
    # Ensure this is called after FKs are potentially modified
    fix_user_constraints_to_work_with_hard_delete(context)

    context.commit()
    print("Database schema upgrade process finished.")
