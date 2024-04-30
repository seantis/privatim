from wtforms.fields.choices import SelectField
from wtforms.widgets.core import Select
from privatim.i18n import _


from typing import Any, TYPE_CHECKING
if TYPE_CHECKING:
    from wtforms.fields.choices import SelectFieldBase
    from markupsafe import Markup


class ChosenSelectWidget(Select):

    def __call__(self, field: 'SelectFieldBase', **kwargs: Any) -> 'Markup':
        if not kwargs.get('class'):
            kwargs['class'] = 'searchable-select'
        else:
            kwargs['class'] += ' searchable-select'
        kwargs['placeholder_'] = _('Select Members...')
        kwargs['autocomplete_'] = 'off'
        return super(ChosenSelectWidget, self).__call__(field, **kwargs)


class SearchableSelectField(SelectField):
    """A multiple select field with tom-select.js support."""

    widget = ChosenSelectWidget(multiple=True)
