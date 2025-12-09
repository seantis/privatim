from __future__ import annotations
from markupsafe import Markup


from typing import TYPE_CHECKING
from collections.abc import Iterator
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.types import RenderData
    from privatim.controls.controls import Button


class ActionMenuEntry:
    def __init__(self, title: str, url: str):
        self.title = title
        self.url = url

    def __call__(self) -> Markup:
        return Markup('<a class="dropdown-item" href="{}">{}</a>').format(
            self.url, self.title
        )

    def __str__(self) -> str:
        return self.__call__()

    def __html__(self) -> str:
        return self.__call__()

    def __repr__(self) -> str:
        return f'<ActionMenuEntry: {self.title}>'


class ActionMenu:
    def __init__(self) -> None:
        self.entries: list[ActionMenuEntry | Button] = []

    def add(self, entry: ActionMenuEntry | Button) -> None:
        self.entries.append(entry)

    def __iter__(self) -> Iterator[ActionMenuEntry | Button]:
        return iter(self.entries)


def action_menu(context: object, request: IRequest) -> RenderData:
    action_menu = getattr(request, 'action_menu_entries', ActionMenu())
    return {'action_menu_entries': action_menu}
