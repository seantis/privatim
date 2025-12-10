from __future__ import annotations
from pyramid.i18n import make_localizer
from pyramid.interfaces import ITranslationDirectories
from pyramid.threadlocal import get_current_registry, get_current_request


def translate(
    term: str, language: str | None = None, domain: str | None = None
) -> str:
    if domain is not None:
        assert domain in {'privatim', 'wtforms'}

    if language is None:
        request = get_current_request()
        if request:
            return request.localizer.translate(term, domain)
        if hasattr(term, 'interpolate'):
            return term.interpolate()
        return term

    reg = get_current_registry()
    localizername = f'localizer{language}'
    localizer = getattr(reg, localizername, None)

    if not localizer:
        translation_dirs = (
            reg.queryUtility(ITranslationDirectories) or []  # type:ignore
        )
        localizer = make_localizer(language, translation_dirs)
        setattr(reg, localizername, localizer)

    return localizer.translate(term)


def pluralize(
    singular: str, plural: str, n: int, language: str | None = None
) -> str:
    if language is None:
        request = get_current_request()
        if request:
            return request.localizer.pluralize(singular, plural, n)
        term = singular if n == 1 else plural
        if hasattr(term, 'interpolate'):
            return term.interpolate()
        return term

    reg = get_current_registry()
    localizername = f'localizer{language}'
    localizer = getattr(reg, localizername, None)

    if not localizer:
        tdirs = reg.queryUtility(ITranslationDirectories) or []  # type:ignore
        localizer = make_localizer(language, tdirs)
        setattr(reg, localizername, localizer)

    return localizer.pluralize(singular, plural, n)
