from sqlalchemy import select
from wtforms import Form, StringField, SelectField
from wtforms.validators import DataRequired

from privatim.i18n import _
from privatim.models import User

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.models import WorkingGroup


class WorkingGroupForm(Form):

    def __init__(
        self,
        context: 'WorkingGroup | None',
        request: 'IRequest',
    ) -> None:

        self.title = _('Edit Working Group')

        super().__init__(
            request.POST,
            obj=context,
            meta={'context': context, 'request': request},
        )

        session = self.meta.request.dbsession
        stmt = select(User)
        users = session.execute(stmt).scalars()

        self.leader_id.choices = tuple(
            [('0', _('No Leader'))] + [(str(u.id), u.fullname) for u in users]
        )

    name: StringField = StringField('Name', validators=[DataRequired()])

    leader_id: SelectField = SelectField(_('Leader'))
