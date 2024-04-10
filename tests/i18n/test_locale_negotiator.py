from privatim.i18n.locale_negotiator import LocaleNegotiator
from privatim.models import User
from privatim.testing import DummyRequest


def test_available_languages(config):
    negotiator = LocaleNegotiator()
    request = DummyRequest()
    assert negotiator.available_languages(request) == []

    config.registry.settings['pyramid.available_languages'] = 'en fr'
    assert negotiator.available_languages(request) == ['en', 'fr']


def test_default_language(config):
    negotiator = LocaleNegotiator()
    request = DummyRequest()
    assert negotiator.default_language(request) == 'en'

    config.registry.settings['pyramid.default_locale_name'] = 'en'
    assert negotiator.default_language(request) == 'en'

    config.registry.settings['pyramid.default_locale_name'] = 'de'
    assert negotiator.default_language(request) == 'de'

    config.registry.settings['pyramid.available_languages'] = 'fr en'
    config.registry.settings['pyramid.default_locale_name'] = 'fr'
    assert negotiator.default_language(request) == 'fr'

    config.registry.settings['pyramid.available_languages'] = 'en de fr'
    config.registry.settings['pyramid.default_locale_name'] = 'de'
    assert negotiator.default_language(request) == 'de'

    config.registry.settings['pyramid.available_languages'] = 'fr'
    config.registry.settings['pyramid.default_locale_name'] = ''
    assert negotiator.default_language(request) == 'fr'


def test_call_user(config, organization, user):
    session = config.dbsession
    config.registry.settings['pyramid.available_languages'] = 'en de fr'
    request = DummyRequest()
    request.accept_language = 'en'
    negotiator = LocaleNegotiator()
    assert negotiator(request) == 'en'

    organization.locale = 'fr'
    session.flush()
    negotiator = LocaleNegotiator()
    assert negotiator(request) == 'fr'


def test_call_browser(config):
    config.registry.settings['pyramid.available_languages'] = 'en de'
    request = DummyRequest()
    request.accept_language = 'de-de, de;q=0.8, en-us;q=0.5, en;q=0.3'
    negotiator = LocaleNegotiator()
    assert negotiator(request) == 'de'


def test_call_fallback(config):
    config.registry.settings['pyramid.default_locale_name'] = 'en'
    request = DummyRequest()
    request.accept_language = 'fr'
    negotiator = LocaleNegotiator()
    assert negotiator(request) == 'en'

    config.registry.settings['pyramid.default_locale_name'] = ''
    config.registry.settings['pyramid.available_languages'] = 'de fr'
    request = DummyRequest()
    assert negotiator(request) == 'de'


def test_call_fallback_no_default(config):
    config.registry.settings['pyramid.default_locale_name'] = ''
    request = DummyRequest()
    negotiator = LocaleNegotiator()
    assert negotiator(request) == 'en'

    config.registry.settings['pyramid.available_languages'] = 'de fr'
    assert negotiator(request) == 'de'


def test_call_order(config, organization):
    session = config.dbsession
    config.registry.settings['pyramid.available_languages'] = 'en de'
    config.registry.settings['pyramid.default_locale_name'] = 'en'
    request = DummyRequest()
    request.accept_language = 'fr'
    negotiator = LocaleNegotiator()
    assert negotiator(request) == 'en'

    request.accept_language = 'de'
    assert negotiator(request) == 'de'

    user = User(
        organization=organization,
        email='test@example.com',
    )
    session.add(user)
    session.flush()
    session.refresh(user)
    config.testing_securitypolicy(userid=user.id)
    assert negotiator(request) == 'en'
