from mimetypes import guess_extension
from pdftotext import PDF  # type: ignore


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from _typeshed import SupportsRead


def word_count(text: str) -> int:
    """The word-count of the given text. Goes through the string exactly
    once and has constant memory usage. Not super sophisticated though.

    """
    if not text:
        return 0

    count = 0
    inside_word = False

    for char in text:
        if char.isspace():
            inside_word = False
        elif not inside_word:
            count += 1
            inside_word = True

    return count


def extract_pdf_info(
    content: 'SupportsRead[bytes]', remove: str = '\0'
) -> tuple[int, str]:
    """Extracts the number of pages and text from a PDF.

    Requires poppler.
    """
    try:
        content.seek(0)  # type:ignore[attr-defined]
    except Exception:  # nosec:B110
        pass

    pages = PDF(content)

    def clean(text: str) -> str:
        for character in remove:
            text = text.replace(character, '')
        return ' '.join(text.split())

    # XXX
    # Rollback the file handle to the beginning
    # This is sort of because of `reindex_files`, because that happens
    # before the file is **actually** saved.
    try:
        content.seek(0)  # type:ignore[attr-defined]
    except Exception:  # nosec:B110
        pass
    return len(pages), ' '.join(clean(page) for page in pages).strip()


def extension_for_content_type(
    content_type: str, filename: str | None = None
) -> str:
    """Gets the extension for the given content type. Note that this is
    *meant for display only*. A file claiming to be a PDF might not be one,
    but this function would not let you know that.

    """

    if filename is not None:
        _, sep, ext = filename.rpartition('.')
        ext = ext.lower() if sep else ''
    else:
        ext = guess_extension(content_type, strict=False) or ''

    return ext.strip('. ')
