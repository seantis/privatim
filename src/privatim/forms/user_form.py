from sqlalchemy import select, exists
from wtforms import SelectMultipleField
from wtforms.fields.simple import StringField, EmailField
from wtforms.validators import Length, DataRequired, Optional, ValidationError
from privatim.forms.core import Form
from privatim.forms.validators import Immutable
from privatim.i18n import _

from typing import TYPE_CHECKING

from privatim.models import User, WorkingGroup

if TYPE_CHECKING:
    from pyramid.interfaces import IRequest


class UserForm(Form):

    def __init__(
        self,
        context: User | None,
        request: 'IRequest',
    ) -> None:
        self._title = _('Filter')
        session = request.dbsession
        super().__init__(
            request.POST,
            obj=context,
            meta={'context': context, 'request': request},
        )
        self.groups.choices = [
            (str(id), name)
            for id, name in session.execute(
                (
                    select(WorkingGroup.id, WorkingGroup.name).order_by(
                        WorkingGroup.name
                    )
                )
            )
        ]

    def validate_email(self, field: EmailField) -> None:
        in_add_mode = self.meta.context is None
        if in_add_mode:
            if field.data:
                field.data = field.data.lower()
            stmt = select(exists().where(User.email == field.data))
            if self.meta.request.dbsession.scalar(stmt):
                raise ValidationError(
                    _('A User with this email already exists.')
                )

    email = EmailField(
        _('Email'),
        validators=[Length(max=255), DataRequired()]
    )

    first_name = StringField(
        _('First Name'), validators=[Length(max=255), DataRequired()]
    )

    last_name = StringField(
        _('Last Name'),
        validators=[Length(max=255), DataRequired()],
    )

    # Adding the user to existing groups
    groups = SelectMultipleField(
        _('Working Groups (multiple selection possible)'),
        validators=[Optional()],
    )

    abbrev = StringField(
        _(
            'Abbreviation (optional). If left blank, the first letter of the '
            'first name and surname will be used.'
        ),
        validators=[Optional(), Length(min=1, max=3)],
    )

    def populate_obj(self, obj: object) -> None:
        for name, field in self._fields.items():

            if any(isinstance(v, Immutable) for v in field.validators or ()):
                continue

            if (isinstance(field, SelectMultipleField) and field.name ==
                    'groups'):
                session = self.meta.request.dbsession
                stmt = select(WorkingGroup).where(
                    WorkingGroup.id.in_(field.raw_data or ()))
                added_group = list(session.execute(stmt).scalars().unique())
                obj.groups = added_group  # type:ignore[attr-defined]
                continue

            field.populate_obj(obj, name)
