from privatim.orm.session import DBSession
from sqlalchemy import asc, select
from privatim.models import Group, WorkingGroup
from wtforms_sqlalchemy.orm import model_form  # type: ignore[import-untyped]
from privatim.i18n import _
from functools import lru_cache


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.types import RenderData
    from sqlalchemy.orm.session import Session
    from wtforms.form import FormMeta


@lru_cache(maxsize=None)
def get_working_group_form(session: 'Session | None' = None) -> 'FormMeta':
    if session is None:
        session = DBSession()
    return model_form(WorkingGroup, db_session=session)


def groups_view(request: 'IRequest') -> 'RenderData':
    session = request.dbsession
    q = select(Group).order_by(asc(Group.name))
    groups = session.execute(q).unique().scalars().all()

    return {'groups': groups}


def group_view(context: WorkingGroup, request: 'IRequest') -> 'RenderData':

    form = get_working_group_form(request.dbsession)
    if request.method == 'POST' and form.validate():
        # breakpoint()
        form.populate_obj(context)

    return {'form': form, 'form_title': _('Add Working Group')}
