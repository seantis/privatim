from sqlalchemy import select
from wtforms import SelectField
from privatim.forms.core import Form
from wtforms.validators import DataRequired

from privatim.forms.fields.fields import ConstantTextAreaField
from privatim.forms.fields.fields import SearchableMultiSelectField
from privatim.i18n import _
from privatim.models import User
from privatim.models import WorkingGroup


from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from wtforms.meta import _MultiDictLike
    from collections.abc import Mapping, Sequence


class WorkingGroupForm(Form):

    def __init__(
        self,
        context: WorkingGroup | None,
        request: 'IRequest',
    ) -> None:

        self._title = _('Edit Working Group')

        super().__init__(
            request.POST if request.POST else None,
            obj=context,
            meta={'context': context, 'request': request},
        )

        session = self.meta.request.dbsession
        users = session.execute(select(User)).scalars().all()

        user_choices = [
            tuple((str(u.id), u.fullname)) for u in sorted(  # noqa:C409
                users, key=lambda u: u.first_name or ''
            )
        ]
        self.leader.choices = [('0', '-'), *user_choices]
        self.users.choices = user_choices
        self.chairman.choices = [('0', '-'), *user_choices]

    name = ConstantTextAreaField(
        _('Name'), validators=[DataRequired()]
    )

    leader = SelectField(_('Leader'))

    users = SearchableMultiSelectField(
        _('Members'), validators=[DataRequired()]
    )

    chairman = SelectField(
        _('Contact Chairman')
    )

    def process(
        self,
        formdata: '_MultiDictLike | None' = None,
        obj: object | None = None,
        data: 'Mapping[str, Any] | None' = None,
        extra_filters: 'Mapping[str, Sequence[Any]] | None' = None,
        **kwargs: Any
    ) -> None:
        super().process(formdata, obj, data, **kwargs)
        if obj is None:
            return None
        if not formdata:
            assert isinstance(obj, WorkingGroup)
            # For the SearchableMultiSelectField we always need to assign
            # the data manually, since there is no 1:1 Mapping
            self.users.data = [str(user.id) for user in obj.users]

            # Without this, the form is not pre-filled in edit
            if obj.leader:
                self.leader.data = str(obj.leader.id)

            if (chairman := getattr(obj, 'chairman', None)) is not None:
                self.chairman.data = str(chairman.id)
