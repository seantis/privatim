from fanstatic import Fanstatic
from pyramid.config import Configurator
from pyramid_beaker import session_factory_from_settings
from sqlalchemy import Table, MetaData, Column, ForeignKey
from sqlalchemy_file import FileField
from email.headerregistry import Address
from privatim.mail import PostmarkMailer
from privatim.orm.uuid_type import UUIDStr as UUIDStrType

from pyramid.settings import asbool
from privatim.file import setup_filestorage
from privatim.flash import MessageQueue
from privatim.i18n import LocaleNegotiator
from privatim.route_factories.root_factory import root_factory
from privatim.security import authenticated_user
from privatim.security_policy import SessionSecurityPolicy

__version__ = '0.0.0'


from typing import Any, TYPE_CHECKING

from privatim.views.profile import user_pic_url

if TYPE_CHECKING:
    from _typeshed.wsgi import WSGIApplication
    from privatim.cli.upgrade import UpgradeContext


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
    config.add_request_method(user_pic_url, 'user_pic', property=True)
    config.add_request_method(MessageQueue, 'messages', reify=True)


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

    app = config.make_wsgi_app()
    return Fanstatic(app, versioning=True)


def upgrade(context: 'UpgradeContext'):  # type: ignore[no-untyped-def]
    if not context.has_table('consultation_assets'):
        consultation_assets = Table(
            'consultation_assets',
            MetaData(),
            Column('id', UUIDStrType, primary_key=True),
            Column(
                'consultation_id', UUIDStrType, ForeignKey('consultations.id')
            ),
            Column('document', FileField),
        )
        consultation_assets.create(context.engine)

    if context.has_column('consultations', 'documents'):
        context.drop_column('consultations', 'documents')

    context.commit()
