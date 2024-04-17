from sqlalchemy import asc, select
from privatim.models import Group


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.types import RenderData


def group_view(request: 'IRequest') -> 'RenderData':
    session = request.dbsession
    q = select(Group).order_by(asc(Group.name))
    groups = session.execute(q).unique().scalars().all()

    return {'groups': groups}
