from __future__ import annotations
from pyramid.events import NewResponse
from .csp_header import csp_header

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.config import Configurator


def register_subscribers(config: 'Configurator') -> None:
    config.add_subscriber(csp_header, NewResponse)
