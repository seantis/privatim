from privatim.utils import flatten_comments
from privatim.views.consultations import trim_filename
from shared.utils import Bunch


def test_empty_comments():
    comments = []

    request = Bunch(**{'comment.user': None})
    assert (
        flatten_comments(
            comments,
            'some-url-whatever',
            request,
        )
        == []
    )


def test_short_filename():
    filename = "short.txt"
    expected_output = "short.txt"
    assert trim_filename(filename) == expected_output


def test_long_filename():
    filename = "this_is_a_very_long_filename_that_exceeds_32_chars.txt"
    expected_output = "this_is_a_very_long_filename...txt"
    assert trim_filename(filename) == expected_output


def test_no_extension():
    filename = "filename_without_extension"
    expected_output = "filename_without_extension"
    assert trim_filename(filename) == expected_output


def test_empty_filename():
    filename = ""
    expected_output = ""
    assert trim_filename(filename) == expected_output


def test_filename_with_dots():
    filename = "file.name.with.dots.txt"
    expected_output = "file.name.with.dots.txt"
    assert trim_filename(filename) == expected_output


def test_filename_with_exactly_32_chars():
    filename = "exactly_32_characters_long.txt"
    expected_output = "exactly_32_characters_long.txt"
    assert trim_filename(filename) == expected_output
