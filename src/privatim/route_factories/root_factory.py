from __future__ import annotations
from typing import TYPE_CHECKING

from privatim.models.root import Root

if TYPE_CHECKING:
    from pyramid.interfaces import IRequest


def root_factory(request: IRequest) -> Root:
    return Root()
