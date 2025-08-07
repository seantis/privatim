from docx import Document
from pdftotext import PDF  # type: ignore
from docx.text.paragraph import Paragraph
from docx.table import Table


from typing import IO, TYPE_CHECKING, Any
from collections.abc import Iterator


if TYPE_CHECKING:
    from _typeshed import SupportsRead
    from privatim.models import AgendaItem
    from docx.blkcntnr import BlockItemContainer


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


def get_docx_text(content: IO[bytes]) -> str:
    doc = Document(content)
    try:
        text = recursively_iter_block_items(doc)  # type: ignore
        return '\n'.join(item.text for item in text)
    except Exception:
        return ''


def recursively_iter_block_items(
    blockcontainer: 'BlockItemContainer',
) -> Iterator[Any]:
    """ Extract text content form docx in the order that it appears. This
    works for tables as well.

    https://github.com/python-openxml/python-docx/issues/40#issuecomment
    -1793226714

    """
    for item in blockcontainer.iter_inner_content():
        if isinstance(item, Paragraph):
            yield item
        elif isinstance(item, Table):
            for row in item.rows:
                for cell in row.cells:
                    yield from recursively_iter_block_items(cell)


def normalize_agenda_item_positions(items: list['AgendaItem']) -> None:
    """
    Normalize positions to ensure they are sequential without duplicates.
    Items are sorted by their current position first, and title as secondary
    sort to ensure consistent ordering when positions are duplicated.
    """
    sorted_items = sorted(items, key=lambda x: (x.position, x.title))
    for i, item in enumerate(sorted_items):
        item.position = i
