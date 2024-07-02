from markupsafe import Markup
from markupsafe import escape
from pyramid.i18n import TranslationString

from privatim.i18n import _
from privatim.i18n import translate
from privatim.i18n.translation_string import TranslationMarkup


def test_translation_string_factory():
    result = _('Just a test')
    assert isinstance(result, TranslationString)
    assert result.domain == 'privatim'


def test_translation_string_factory_markup():
    result = _(Markup('Just a test'))
    assert isinstance(result, TranslationMarkup)
    assert isinstance(result.default, Markup)
    assert result.domain == 'privatim'


def test_translation_string_factory_markup_param():
    result = _('Just a test', markup=True)
    assert isinstance(result, TranslationMarkup)
    assert isinstance(result.default, Markup)
    assert result.domain == 'privatim'


def test_translate():
    msg = TranslationString('Translate me')
    result = translate(msg, 'de')
    assert result == 'Translate me'


def test_translate_markup():
    msg = TranslationMarkup('<b>bold</b>')
    result = translate(msg, 'de')
    assert isinstance(result, Markup)
    assert result == Markup('<b>bold</b>')


def test_translate_translation_dirs(pg_config):
    pg_config.add_translation_dirs('privatim:locale/')
    # Testing localizer doesn't seem to work.
    pg_config.registry.localizer_de = None
    msg = _('Just a test')
    assert translate(msg, 'en') == 'Just a test'
    assert translate(msg, 'de') == 'Nur ein Test'


def test_translate_translation_dirs_markup(pg_config):
    pg_config.add_translation_dirs('privatim:locale/')
    # Testing localizer doesn't seem to work.
    pg_config.registry.localizer_de = None
    msg = _('<b>bold</b>', markup=True)
    assert escape(translate(msg, 'en')) == Markup('<b>bold</b>')
    assert escape(translate(msg, 'de')) == Markup('<b>fett</b>')


def test_translate_translation_dirs_markup_omitted(pg_config):
    pg_config.add_translation_dirs('privatim:locale/')
    # Testing localizer doesn't seem to work.
    pg_config.registry.localizer_de = None
    msg = _('<b>bold</b>')
    assert escape(translate(msg, 'en')) == Markup('&lt;b&gt;bold&lt;/b&gt;')
    assert escape(translate(msg, 'de')) == Markup('&lt;b&gt;fett&lt;/b&gt;')
