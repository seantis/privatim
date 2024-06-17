from markupsafe import Markup


from typing import Any, TYPE_CHECKING
if TYPE_CHECKING:
    from wtforms import Field, FormField


class LineWidget:

    def render_field(self, field: 'Field') -> Markup:

        return Markup(
            '<div class="col-auto">'
            '{label}'
            '{input}'
            '{errors}'
            '</div>'
        ).format(
            label=field.label(),
            input=field(),
            errors=Markup('').join(
                Markup('<div class="invalid-feedback">{}</div>').format(e)
                for e in field.errors
            )
        )

    def __call__(self, field: 'FormField[Any]', **kwargs: Any) -> Markup:
        return Markup(
            '<div class="row mb-3">{}</div>'
        ).format(Markup('').join(self.render_field(f) for f in field.form))
