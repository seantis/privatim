from pyramid.httpexceptions import HTTPBadRequest
from pyramid.interfaces import ILocaleNegotiator
from zope.interface import implementer


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest


@implementer(ILocaleNegotiator)
class LocaleNegotiator:

    def available_languages(self, request: 'IRequest') -> list[str]:
        settings = request.registry.settings
        return settings.get('pyramid.available_languages', '').split()

    def default_language(self, request: 'IRequest') -> str:
        settings = request.registry.settings
        default = settings.get('pyramid.default_locale_name', None)
        if default:
            return default

        available = self.available_languages(request)
        return available[0] if available else 'de'

    def __call__(self, request: 'IRequest') -> str:
        available = self.available_languages(request)
        default = self.default_language(request)

        # Store in session if locale name is set explictly
        locale: str | None = None
        try:
            locale_ = request.params.get('set_language', None)
            if isinstance(locale_, str):
                locale = locale_
        except ValueError as e:
            if not request.exception:
                raise HTTPBadRequest(str(e)) from None

        if locale and locale in available:
            request.session['locale_name'] = locale
            return locale

        # 1. Try to get locale name from the session
        locale = request.session.get('locale_name', None)
        if locale and locale in available:
            return locale

        # 2. Get language from user object
        user = request.user
        if user:
            locale = user.locale
            if locale and locale in available:
                return locale

        # 3. Use browser's Accept-Language header
        locale = request.accept_language.lookup(available, default=default)
        if locale and locale in available:
            return locale

        # 4. Fallback to default language
        return default
