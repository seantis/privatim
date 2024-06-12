from privatim.utils import maybe_escape


def test_maybe_escape():
    assert maybe_escape(None) == ''
    assert maybe_escape('<') == '&lt;'
    assert maybe_escape('>') == '&gt;'
