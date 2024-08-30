from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.events import NewResponse
    from pyramid.interfaces import IRequest


def default_csp_directives(request: 'IRequest') -> dict[str, str]:
    directives = {
        "base-uri": "'self'",
        "child-src": "blob:",
        "connect-src": "'self'",
        "default-src": "'none'",
        "font-src": "'self'",
        "form-action": "'self'",
        "frame-ancestors": "'none'",
        "img-src":  "'self' data: blob:",
        "object-src": "'self'",
        # enable one inline script by hash TomSelectWidget
        "script-src": "'self' blob: resource: "
                      "'sha256-V1F76Rpg0OFOeNZAMAgQoR2STCnYJj8IyDvTdgzYHpQ='",
        "style-src": "'self' 'unsafe-inline'",
    }

    sentry_dsn = request.registry.settings.get('sentry_dsn')
    if sentry_dsn:
        key = sentry_dsn.split('@')[0].split('/')[-1].split(':')[0]
        host = sentry_dsn.split('@')[1].split('/')[0]
        project = sentry_dsn.split('/')[-1]
        url = f'https://sentry.io/api/{project}/security/?sentry_key={key}'
        directives['report-uri'] = url
        directives['connect-src'] += f' https://{host}'
    return directives


def csp_header(event: 'NewResponse') -> None:
    response = event.response
    if 'Content-Security-Policy' not in response.headers:
        directives = default_csp_directives(event.request)
        csp = '; '.join([f'{k} {v}' for k, v in directives.items()])
        response.headers['Content-Security-Policy'] = csp
