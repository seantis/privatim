from __future__ import annotations
from markupsafe import Markup
from privatim.controls.controls import html_params


from typing import Any
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from wtforms import Field


class CheckboxListWidget:

    def __init__(self, inline: bool = False):
        self.inline = inline

    def __call__(self, field: 'Field', **kwargs: Any) -> Markup:
        kwargs.setdefault('id', field.id)
        css_class = 'form-check'
        if self.inline:
            css_class += 'form-check-inline'
        if (extra := kwargs.get('class')):
            css_class = f'{css_class} {extra}'

        kwargs['class'] = css_class
        assert hasattr(field, '__iter__')
        return Markup('').join(
            Markup(
                '<div {params}>'
                '{input}'
                '{label}'
                '</div>'
            ).format(
                params=html_params(**kwargs),
                input=subfield(class_='form-check-input'),
                label=subfield.label(class_='form-check-label')
            )
            for subfield in field
        )
