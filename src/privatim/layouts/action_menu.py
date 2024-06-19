from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.types import RenderData


class ActionMenuEntry:
    def __init__(self, title: str, url: str):
        self.title = title
        self.url = url

    def __call__(self) -> str:
        return f'<a class="dropdown-item" href="{self.url}">{self.title}</a>'

    def __str__(self) -> str:
        return self.__call__()

    def __html__(self) -> str:
        return self.__call__()

    def __repr__(self) -> str:
        return f'<ActionMenuEntry: {self.title}>'


def action_menu(context: object, request: 'IRequest') -> 'RenderData':
    action_menu_entries = getattr(request, 'action_menu_entries', [])
    return {'action_menu_entries': action_menu_entries}
