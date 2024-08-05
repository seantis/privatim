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

    return len(pages), ' '.join(clean(page) for page in pages).strip()
