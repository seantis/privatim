from __future__ import annotations
from . import models


from typing import Any


def setup(env: dict[str, Any]) -> None:
    request = env['request']

    # start a transaction
    request.tm.begin()

    # inject some vars into the shell builtins
    env['tm'] = request.tm
    env['dbsession'] = request.dbsession
    env['models'] = models
