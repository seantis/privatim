from pyramid.i18n import make_localizer
from pyramid.interfaces import ITranslationDirectories
from pyramid.threadlocal import get_current_registry
from pyramid.threadlocal import get_current_request


def translate(
    term:     str,
    language: str | None = None
) -> str:

    if language is None:
        request = get_current_request()
        if request:
            return request.localizer.translate(term)
        elif hasattr(term, 'interpolate'):
            return term.interpolate()
        return term
    else:
        reg = get_current_registry()
        localizer_name = f'localizer_{language}'
        localizer = getattr(reg, localizer_name, None)
        if not localizer:
            tdirs: list[str]
            tdirs = reg.queryUtility(ITranslationDirectories, default=[])
            localizer = make_localizer(language, tdirs)
            setattr(reg, localizer_name, localizer)

        return localizer.translate(term)


def pluralize(
    singular: str,
    plural:   str,
    n:        int,
    language: str | None = None
) -> str:

    if language is None:
        request = get_current_request()
        if request:
            return request.localizer.pluralize(singular, plural, n)

        # technically the condition depends on the language, but since
        # we fall back to interpolate anyways n==1 is the correct choice
        term = singular if n == 1 else plural
        if hasattr(term, 'interpolate'):
            return term.interpolate()
        return term
    else:
        reg = get_current_registry()
        localizer_name = f'localizer_{language}'
        localizer = getattr(reg, localizer_name, None)
        if not localizer:
            tdirs: list[str]
            tdirs = reg.queryUtility(ITranslationDirectories, default=[])
            localizer = make_localizer(language, tdirs)
            setattr(reg, localizer_name, localizer)

        return localizer.pluralize(singular, plural, n)
