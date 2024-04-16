from markupsafe import Markup

from privatim.i18n.translation_string import TranslationMarkup
from privatim.i18n.translation_string import TranslationString


def test_init():
    markup = TranslationMarkup('<b>bold</b>')
    assert str(markup) == '<b>bold</b>'
    assert isinstance(markup.interpolate(), Markup)
    assert markup.interpolate() == Markup('<b>bold</b>')
    assert Markup(markup) == Markup('<b>bold</b>')  # noqa: MS001
    assert markup.domain is None
    assert markup.mapping is None
    assert markup.context is None
    assert isinstance(markup.default, Markup)
    assert markup.default == Markup(markup)  # noqa: MS001


def test_init_mapping_plain():
    markup = TranslationMarkup(
        '<b>${arg}</b>',
        mapping={'arg': '<i>unsafe</i>'}
    )
    assert markup.mapping == {'arg': Markup('&lt;i&gt;unsafe&lt;/i&gt;')}
    assert markup.interpolate() == Markup('<b>&lt;i&gt;unsafe&lt;/i&gt;</b>')


def test_init_mapping_markup():
    markup = TranslationMarkup(
        '<b>${arg}</b>',
        mapping={'arg': Markup('<i>italic</i>')}
    )
    assert markup.mapping == {'arg': Markup('<i>italic</i>')}
    assert markup.interpolate() == Markup('<b><i>italic</i></b>')


def test_init_translation_string():
    plain = TranslationString(
        '<b>${arg}</b>',
        mapping={'arg': '<i>unsafe</i>'},
        domain='privatim',
        default='<u>${arg}</u>',
        context='context',
    )
    markup = TranslationMarkup(plain)
    assert str(markup) == '<b>${arg}</b>'
    assert markup.domain == 'privatim'
    assert isinstance(markup.default, Markup)
    assert markup.default == Markup('<u>${arg}</u>')
    assert markup.mapping == {'arg': Markup('&lt;i&gt;unsafe&lt;/i&gt;')}
    assert markup.interpolate() == Markup('<u>&lt;i&gt;unsafe&lt;/i&gt;</u>')


def test_escape():
    unsafe = TranslationString('<b>unsafe</b>', domain='privatim')
    escaped = TranslationMarkup.escape(unsafe)
    assert escaped.domain == 'privatim'
    assert str(escaped) == '&lt;b&gt;unsafe&lt;/b&gt;'
    assert escaped.interpolate() == Markup('&lt;b&gt;unsafe&lt;/b&gt;')


def test_mod_markup():
    markup = TranslationMarkup('<b>${arg}</b>')
    updated = markup % {'arg': Markup('<i>italic</i>')}
    assert updated.mapping == {'arg': Markup('<i>italic</i>')}
    assert updated.interpolate() == Markup('<b><i>italic</i></b>')


def test_mod_plain():
    markup = TranslationMarkup('<b>${arg}</b>')
    updated = markup % {'arg': '<i>unsafe</i>'}
    assert updated.mapping == {'arg': Markup('&lt;i&gt;unsafe&lt;/i&gt;')}
    assert updated.interpolate() == Markup('<b>&lt;i&gt;unsafe&lt;/i&gt;</b>')


def test_interpolate():
    markup = TranslationMarkup('<b>bold</b>')
    assert markup.interpolate() == Markup('<b>bold</b>')
    assert markup.interpolate('<b>fett</b>') == Markup('<b>fett</b>')


def test_html():
    markup = TranslationMarkup('<b>bold</b>')
    assert markup.__html__() == Markup('<b>bold</b>')
