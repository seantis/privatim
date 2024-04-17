from typing import TYPE_CHECKING

from sqlalchemy import asc, select

from privatim.models import Group


if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.types import RenderData


def group_view(request: 'IRequest') -> 'RenderData':
    # query all the working groups

    session = request.dbsession

    q = select(Group).order_by(asc(Group.name))
    groups = session.execute(q).all()

    return {'groups': groups}
