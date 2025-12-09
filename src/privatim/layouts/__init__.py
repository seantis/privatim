from __future__ import annotations
from typing import TYPE_CHECKING

from privatim.layouts.action_menu import action_menu

from .flash import flash
from .layout import Layout
from .navbar import navbar
from .footer import footer


if TYPE_CHECKING:
    from pyramid.config import Configurator


def includeme(config: Configurator) -> None:
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

    config.add_panel(
        panel=footer,
        name='footer',
        renderer='footer.pt'
    )

    config.add_panel(
        panel=action_menu,
        name='action_menu',
        renderer='action_menu.pt'
    )
