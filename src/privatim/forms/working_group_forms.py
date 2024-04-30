from sqlalchemy import select
from wtforms import Form, StringField, SelectField
from wtforms.validators import DataRequired

from privatim.forms.fields import SearchableSelectField
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
        users = session.execute(select(User)).scalars().all()

        user_choices = tuple(
            (str(u.id), u.fullname) for u in sorted(
                users, key=lambda u: u.first_name
            )
        )
        self.leader_id.choices = (('0', _('No Leader')),) + user_choices
        self.users.choices = user_choices

    name: StringField = StringField(_('Name'), validators=[DataRequired()])

    leader_id: SelectField = SelectField(_('Leader'))

    users: SearchableSelectField = SearchableSelectField(_('Members'))
