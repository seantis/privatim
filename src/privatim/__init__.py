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
from privatim.orm.uuid_type import UUIDStr as UUIDStrType

from pyramid.settings import asbool
from privatim.file.setup import setup_filestorage
from privatim.flash import MessageQueue
from privatim.i18n import LocaleNegotiator
from privatim.route_factories.root_factory import root_factory
from privatim.security import authenticated_user
from privatim.security_policy import SessionSecurityPolicy
from privatim.sms.sms_gateway import ASPSMSGateway

__version__ = '0.0.0'


from typing import Any, TYPE_CHECKING, Iterable
if TYPE_CHECKING:
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

    config.add_request_method(profile_pic, 'profile_pic', property=True)
    config.add_request_method(MessageQueue, 'messages', reify=True)

    def add_action_menu_entries(
        request: 'IRequest',
        entries: Iterable['Button'],
    ) -> None:
        """
        Add multiple Button entries to the action menu.
        """
        if not hasattr(request, 'action_menu_entries'):
            request.action_menu_entries = []
        request.action_menu_entries.extend(entries)

    config.add_request_method(
        lambda request: partial(add_action_menu_entries, request),
        'add_action_menu_entries',
        reify=True,
    )


def add_renderer_globals(event: BeforeRender) -> None:
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
        # Add all other foreign key constraints here
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
                    f" {str(e)}"
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
                f"{str(e)}"
            )


def upgrade(context: 'UpgradeContext'):  # type: ignore[no-untyped-def]

    if not context.has_column('consultations', 'creator_id'):
        context.add_column(
            'consultations',
            Column(
                'creator_id',
                UUIDStrType,
                ForeignKey('users.id', ondelete='SET NULL'),
                nullable=True,
            ),
        )

    context.add_column(
        'meetings',
        Column(
            'created',
            TIMESTAMP(timezone=False),
            server_default=func.now()
        )
    )
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
    context.operations.alter_column(
        'users',
        'first_name',
        existing_type=VARCHAR(length=256),
        nullable=False,
        server_default='',
    )

    context.operations.alter_column(
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

    context.commit()
