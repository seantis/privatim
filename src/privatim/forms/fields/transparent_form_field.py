from __future__ import annotations
from markupsafe import Markup
from wtforms import FormField
from wtforms import Label

from ..widgets import LineWidget


from typing import Any, TypeVar, TYPE_CHECKING
if TYPE_CHECKING:
    from wtforms.fields.core import _Widget
    from wtforms.form import BaseForm
    from wtforms.meta import _SupportsGettextAndNgettext, DefaultMeta
    from privatim.forms.core import Form

    _BoundFormT = TypeVar('_BoundFormT', bound=Form)

    class TransparentFormField(FormField[_BoundFormT]):
        def __init__(
            self: TransparentFormField[_BoundFormT],
            form_class: type[_BoundFormT],
            label: str | None = None,
            validators: None = None,
            separator: str = "-",
            *,
            description: str = "",
            id: str | None = None,
            default: object | None = None,
            widget: _Widget[TransparentFormField[_BoundFormT]] | None = None,
            render_kw: dict[str, Any] | None = None,
            name: str | None = None,
            _form: BaseForm | None = None,
            _prefix: str = "",
            _translations: _SupportsGettextAndNgettext | None = None,
            _meta: DefaultMeta | None = None,
        ) -> None: ...

        process: None  # type:ignore[assignment]
else:

    class TransparentFormField(FormField):
        """ A FormField where the fields get proxied transparently into
        the form it is used in, as if the fields were originally defined
        in that form to begin with.
        """

        label: Label
        widget = LineWidget()

        def __init__(self, form_class: type[Form], **kwargs: Any):
            super().__init__(form_class, **kwargs)
            self.label = _NoLabel(self.label)

        def populate_obj(self, obj: object, name: str) -> None:
            self.form.populate_obj(obj)

        # NOTE: Make sure this can't be called
        process = None


class _NoLabel(Label):

    def __init__(self, label: Label):
        self.field_id = label.field_id
        self.text = label.text

    def __call__(self, text: str | None = None, **kwargs: Any) -> Markup:
        return Markup('')
