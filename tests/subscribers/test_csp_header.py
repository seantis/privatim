from pyramid.events import NewResponse

from privatim.testing import DummyRequest
from subscribers.csp_header import csp_header


def test_csp_header(pg_config):
    request = DummyRequest()
    response = request.response
    event = NewResponse(request, response)
    csp_header(event)
    assert response.headers['Content-Security-Policy'] == (
        "base-uri 'self'; "
        "child-src blob:; "
        "connect-src 'self'; "
        "default-src 'none'; "
        "font-src 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'; "
        "img-src 'self' data: blob:; "
        "object-src 'self'; "
        "script-src 'self' blob: resource: "
        "'sha256-V1F76Rpg0OFOeNZAMAgQoR2STCnYJj8IyDvTdgzYHpQ='; "
        "style-src 'self' 'unsafe-inline'"
    )


def test_csp_header_sentry(pg_config):
    pg_config.registry.settings['sentry_dsn'] = 'https://aa:zz@sentry.io/22'
    request = DummyRequest()
    response = request.response
    event = NewResponse(request, response)
    csp_header(event)
    assert response.headers['Content-Security-Policy'] == (
        "base-uri 'self'; "
        "child-src blob:; "
        "connect-src 'self' https://sentry.io; "
        "default-src 'none'; "
        "font-src 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'; "
        "img-src 'self' data: blob:; "
        "object-src 'self'; "
        "script-src 'self' blob: resource: "
        "'sha256-V1F76Rpg0OFOeNZAMAgQoR2STCnYJj8IyDvTdgzYHpQ='; "
        "style-src 'self' 'unsafe-inline'; "
        "report-uri https://sentry.io/api/22/security/?sentry_key=aa"
    )

    pg_config.registry.settings['sentry_dsn'] = ('https://aa@1.ingest.sentry'
                                                 '.io/22')
    request = DummyRequest()
    response = request.response
    event = NewResponse(request, response)
    csp_header(event)
    assert response.headers['Content-Security-Policy'] == (
        "base-uri 'self'; "
        "child-src blob:; "
        "connect-src 'self' https://1.ingest.sentry.io; "
        "default-src 'none'; "
        "font-src 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'; "
        "img-src 'self' data: blob:; "
        "object-src 'self'; "
        "script-src 'self' blob: resource: "
        "'sha256-V1F76Rpg0OFOeNZAMAgQoR2STCnYJj8IyDvTdgzYHpQ='; "
        "style-src 'self' 'unsafe-inline'; "
        "report-uri https://sentry.io/api/22/security/?sentry_key=aa"
    )


def test_csp_header_existing(pg_config):
    request = DummyRequest()
    response = request.response
    response.headers['Content-Security-Policy'] = "base-uri 'self';"
    event = NewResponse(request, response)
    csp_header(event)
    assert response.headers['Content-Security-Policy'] == "base-uri 'self';"
