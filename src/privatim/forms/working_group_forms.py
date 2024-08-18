from sqlalchemy import select
from wtforms import StringField, SelectField
from privatim.forms.core import Form
from wtforms.validators import DataRequired

from privatim.forms.fields.fields import SearchableMultiSelectField
from privatim.i18n import _
from privatim.models import User


from privatim.models import WorkingGroup
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from wtforms.fields.choices import _Choice


class WorkingGroupForm(Form):

    def __init__(
        self,
        context: WorkingGroup | None,
        request: 'IRequest',
    ) -> None:

        self._title = _('Edit Working Group')

        super().__init__(
            request.POST,
            obj=context,
            meta={'context': context, 'request': request},
        )

        session = self.meta.request.dbsession
        users = session.execute(select(User)).scalars().all()

        user_choices: list[_Choice] = [
            (str(u.id), u.fullname) for u in sorted(
                users, key=lambda u: u.first_name or ''
            )
        ]
        self.leader.choices = [('0', _('No Leader'))] + user_choices
        self.users.choices = user_choices

    name: StringField = StringField(_('Name'), validators=[DataRequired()])

    leader: SelectField = SelectField(_('Leader'))

    users: SearchableMultiSelectField = SearchableMultiSelectField(
        _('Members'), validators=[DataRequired()]
    )

    chairman_contact: StringField = StringField(_('Contact Chairman'))
