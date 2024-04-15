from pyramid.interfaces import ILocaleNegotiator


class I18NConfiguratorMixin:
    def set_locale_negotiator(
        self,
        negotiator: ILocaleNegotiator | str
    ) -> None: ...
    def add_translation_dirs(self, *specs: str, override: bool = ...) -> None: ...
