from typing import TYPE_CHECKING

from .flash import flash
from .layout import Layout
from .navbar import navbar


if TYPE_CHECKING:
    from pyramid.config import Configurator


def includeme(config: 'Configurator') -> None:
    config.add_layout(
        Layout,
        'layout.pt'
    )

    config.add_panel(
        panel=flash,
        name='flash',
        renderer='flash.pt'
    )

    config.add_panel(
        panel=navbar,
        name='navbar',
        renderer='navbar.pt'
    )
