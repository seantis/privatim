from typing import Any, TYPE_CHECKING


if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from ..types import RenderData


class NavbarEntry:
    title: str
    url: str
    active: bool

    def __init__(self, request: 'IRequest', title: str, url: str):
        self.title = title
        self.url = url
        self.active = request.path_url == url

    def __call__(self) -> str:
        item_class = 'nav-item'
        link_class = 'nav-link'
        current = ''
        if self.active:
            item_class += ' active'
            link_class += ' active'
            current = ' aria-current="page"'
        return (
            f'<li class="{item_class}">'
            f'<a class="{link_class}" href="{self.url}"{current}>'
            f'{self.title}</a>'
            '</li>'
        )

    def __str__(self) -> str:
        return self.__call__()

    def __html__(self) -> str:
        return self.__call__()


def navbar(context: object, request: 'IRequest') -> 'RenderData':
    return {
        'entries': [
            NavbarEntry(
                request, 'Activities', request.route_url('activities')
            ),
        ]
    }
