from functools import partial
from fanstatic import Fanstatic

from pyramid.events import BeforeRender
from privatim import helpers
from privatim.layouts.action_menu import ActionMenuEntry
from pyramid.config import Configurator
from pyramid_beaker import session_factory_from_settings
from sqlalchemy import Column, ForeignKey, TIMESTAMP, func
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

    # for column in [
    #     'title',
    #     'description',
    #     'recommendation',
    #     'evaluation_result',
    #     'decision',
    # ]:
    #     if context.has_column('consultations', column):
    #         col_info = context.get_column_info('consultations', column)
    #         if col_info and not isinstance(col_info['type'], MarkupText):
    #             context.operations.alter_column(
    #                 'consultations',
    #                 column,
    #                 type_=MarkupText,
    #                 existing_type=col_info['type'],
    #                 nullable=col_info['nullable']
    #             )
    #
    # # Upgrade Meeting model
    # for column in ['name', 'decisions']:
    #     if context.has_column('meetings', column):
    #         col_info = context.get_column_info('meetings', column)
    #         if col_info and not isinstance(col_info['type'], MarkupText):
    #             context.operations.alter_column(
    #                 'meetings',
    #                 column,
    #                 type_=MarkupText,
    #                 existing_type=col_info['type'],
    #                 nullable=col_info['nullable']
    #             )
    # # Upgrade AgendaItem model
    # for column in ['title', 'description']:
    #     if context.has_column('agenda_items', column):
    #         col_info = context.get_column_info('agenda_items', column)
    #         if col_info and not isinstance(col_info['type'], MarkupText):
    #             context.operations.alter_column(
    #                 'agenda_items',
    #                 column,
    #                 type_=MarkupText,
    #                 existing_type=col_info['type'],
    #                 nullable=col_info['nullable']
    #             )
    #
    # # Upgrade Comment model
    # if context.has_table('comments'):
    #     if context.has_column('comments', 'content'):
    #         col_info = context.get_column_info('comments', 'content')
    #         if col_info and not isinstance(col_info['type'], MarkupText):
    #             context.operations.alter_column(
    #                 'comments',
    #                 'content',
    #                 type_=MarkupText,
    #                 existing_type=col_info['type'],
    #                 nullable=col_info['nullable']
    #             )
    #

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
    context.commit()
