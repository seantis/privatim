from typing import TYPE_CHECKING

from pyramid.interfaces import ILocaleNegotiator
from zope.interface import implementer

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
        return available[0] if available else 'en'

    def __call__(self, request: 'IRequest') -> str:
        available = self.available_languages(request)
        default = self.default_language(request)

        locale: str | None


        # 1. Use browser's Accept-Language header
        locale = request.accept_language.lookup(available, default=default)
        if locale and locale in available:
            return locale

        # 2. Fallback to default language
        return default
