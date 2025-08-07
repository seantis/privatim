from __future__ import annotations
from markupsafe import Markup
from wtforms import validators, Label
from wtforms.fields.choices import RadioField
from wtforms.fields.simple import TextAreaField
from wtforms.validators import ValidationError
from wtforms.widgets.core import ListWidget, html_params

from privatim.forms.core import Form
from privatim.forms.fields.fields import ConstantTextAreaField
from privatim.forms.meeting_form import CheckboxField
from privatim.i18n import _, translate
from privatim.models import Meeting
from privatim.utils import datetime_format

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.models import AgendaItem


class AgendaItemForm(Form):

    def __init__(
        self,
        context: 'Meeting | AgendaItem',
        request: 'IRequest',
    ) -> None:

        self._title = (
            _('Add Agenda Item') if isinstance(context, Meeting) else
            _('Edit Agenda Item')
        )

        super().__init__(
            request.POST if request.POST else None,
            obj=context,
            meta={'context': context, 'request': request},
        )

    title = ConstantTextAreaField(
        label=_('Title'),
        validators=[validators.DataRequired()],
        render_kw={'rows': 3}
    )
    description = TextAreaField(
        _('Potentially Description'), render_kw={'rows': 5}
    )

    def populate_obj(self, obj: 'AgendaItem') -> None:  # type:ignore[override]
        super().populate_obj(obj)
        for name, field in self._fields.items():
            field.populate_obj(obj, name)


class MeetingRadioRenderer(ListWidget):

    def __call__(
        self, field: RadioField, **kwargs: Any  # type:ignore[override]
    ) -> Markup:
        kwargs.setdefault('id', field.id)
        kwargs.setdefault('class', 'list-group')
        html_list: list[str] = [f'<{self.html_tag} {html_params(**kwargs)}>']
        for value, label, __, data in field.iter_choices():
            html_list.append('<li class="list-group-item">')
            html_list.append(self.render_radio(field, value, label))
            date = datetime_format(data['time'], format='%d.%m.%y')
            translated = translate(_('Date:'))
            if 'time' in data:
                html_list.append('<br>')
                html_list.append('<small class="text-muted ms-4">')
                html_list.append(f'{translated} {date}')
                html_list.append('</small>')
            html_list.append('</li>')
        html_list.append(f'</{self.html_tag}>')
        return Markup(''.join(html_list))

    def render_radio(self, field: RadioField, value: Any, label: str) -> str:
        name = field.name
        input_id = f'{field.id}-{value}'
        params = {
            'type': 'radio',
            'name': name,
            'id': input_id,
            'value': value,
            'class': 'form-check-input',
        }
        if field.data == value:
            params['checked'] = 'checked'
        return (
            f'<input {html_params(**params)}> '
            f'<label class="form-check-label" for="{input_id}">{label}</label>'
        )


class AgendaItemCopyForm(Form):

    def __init__(
        self,
        context: Meeting,
        request: 'IRequest',
        available_meetings: list[Meeting]
    ) -> None:

        self._title = _('Source')

        super().__init__(
            request.POST if request.POST else None,
            obj=context,
            meta={'context': context, 'request': request},
        )

        self.copy_from.choices = [
            (str(meeting.id), meeting.name, {'time': meeting.time})
            for meeting in available_meetings
        ]

        meeting_link = Markup(
            f'<a href="{request.route_url("meeting", id=context.id)}" '
            'target="_blank" rel="noopener">'
            f'{context.name}</a>'
        )
        translated_text = translate(
            _(
                'The agenda items of the following meeting is copied to '
                '${meeting}',
                mapping={'meeting': meeting_link},
            ),
            request.locale_name,
        )
        self.copy_from.label = Label(
            self.copy_from.id, Markup(translated_text)
        )

        if not available_meetings:
            assert isinstance(self.copy_from.validators, list)
            self.copy_from.validators.append(
                lambda form, field: ValidationError(
                    _('No valid destination meetings available.')
                )
            )

    copy_from = RadioField(
        label=_('Copy agenda items from meeting'),
        validators=[validators.DataRequired()],
        widget=MeetingRadioRenderer(),
    )

    copy_description = CheckboxField(
        _('Copy description aswell'),
        default=False,
    )

    def populate_obj(self, obj: 'AgendaItem') -> None:  # type:ignore[override]
        super().populate_obj(obj)
        for name, field in self._fields.items():
            field.populate_obj(obj, name)
