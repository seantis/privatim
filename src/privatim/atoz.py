from collections import OrderedDict
from itertools import groupby


from typing import Generic, TypeVar, TYPE_CHECKING
if TYPE_CHECKING:
    from collections.abc import Sequence
    from pyramid.interfaces import IRequest


_T = TypeVar('_T')


class AtoZ(Generic[_T]):

    def __init__(self, request: 'IRequest') -> None:
        self.request = request

    def sortkey(self, item: _T) -> str:
        return self.get_title(item)[0].upper()

    def get_items_by_letter(self) -> dict[str, tuple[_T, ...]]:
        items_by_letter = OrderedDict()

        for letter, items in groupby(self.get_items(), self.sortkey):
            items_by_letter[letter] = tuple(
                sorted(items, key=lambda i: self.get_title(i))
            )

        return items_by_letter

    def get_title(self, item: _T) -> str:
        raise NotImplementedError

    def get_items(self) -> 'Sequence[_T]':
        raise NotImplementedError
