from functools import partial
from fanstatic import Fanstatic

from pyramid.events import BeforeRender
from sqlalchemy.dialects.postgresql import TSVECTOR

from privatim import helpers
from privatim.layouts.action_menu import ActionMenuEntry
from pyramid.config import Configurator
from pyramid_beaker import session_factory_from_settings
from sqlalchemy import Column, ForeignKey, String, TIMESTAMP, func, Computed
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

    def add_action_menu_entry(
        request: 'IRequest',
        title: str,
        url: str,
    ) -> None:
        """  The entries are temporarily stored on the request object. They are
        then retrieved in action_menu.py
        """
        if not hasattr(request, 'action_menu_entries'):
            request.action_menu_entries = []
        request.action_menu_entries.append(ActionMenuEntry(title, url))

    config.add_request_method(
        lambda request: partial(add_action_menu_entry, request),
        'add_action_menu_entry',
        reify=True
    )

    def add_action_menu_entries(
        request: 'IRequest',
        entries: Iterable[tuple[str, str]],
    ) -> None:
        if not hasattr(request, 'action_menu_entries'):
            request.action_menu_entries = []
        for title, url in entries:
            request.action_menu_entries.append(ActionMenuEntry(title, url))

    config.add_request_method(
        lambda request: partial(add_action_menu_entries, request),
        'add_action_menu_entries', reify=True)


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


def upgrade(context: 'UpgradeContext'):  # type: ignore[no-untyped-def]

    if not context.has_column('consultations', 'creator_id'):
        context.add_column(
            'consultations',
            Column(
                'creator_id',
                UUIDStrType,
                ForeignKey('users.id'),
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
                ForeignKey('users.id'),
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

    # this needs to be added in the second run
    # context.operations.create_index(
    #     'idx_searchable_files_searchable_text_de_CH',
    #     'searchable_files',
    #     ['searchable_text_de_CH'],
    #     postgresql_using='gin',
    # )

    context.commit()
