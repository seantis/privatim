from functools import partial
from wtforms import Form as BaseForm
from wtforms import Label
from wtforms.meta import DefaultMeta

from privatim.i18n import pluralize
from privatim.i18n import translate
from privatim.i18n import _

from .fields import TransparentFormField
from .validators import Immutable
from .widgets import CheckboxListWidget


from typing import Any, TypeVar, TYPE_CHECKING
if TYPE_CHECKING:
    from _typeshed import SupportsItems
    from collections.abc import Callable, Mapping, MutableMapping, Sequence
    from markupsafe import Markup
    from wtforms import Field
    from wtforms.fields.core import UnboundField
    from wtforms.form import BaseForm as _BaseForm
    from wtforms.meta import _MultiDictLike

    _FieldT = TypeVar('_FieldT', bound=Field)


def update_field_class(
        field: 'Field',
        original_post_validate: 'Callable[[_BaseForm, bool], Any]',
        form: '_BaseForm',
        validation_stopped: bool
) -> None:

    original_post_validate(form, validation_stopped)
    if field.errors:
        field.render_kw['class'] += ' is-invalid'


class PyramidTranslations:

    def gettext(self, string: str) -> str:
        # Note: Need to create a TranslationString again
        return translate(_(string))

    def ngettext(self, singular: str, plural: str, n: int) -> str:
        return pluralize(singular, plural, n)


class BootstrapMeta(DefaultMeta):

    def bind_field(
            self,
            form:          '_BaseForm',
            unbound_field: 'UnboundField[_FieldT]',
            options:       'MutableMapping[str, Any]'
    ) -> 'Field':
        # NOTE: This adds bootstrap specific field classes to render_kw
        render_kw = unbound_field.kwargs.get('render_kw', {})
        field_type = unbound_field.field_class.__name__
        if field_type in ('SelectField', 'SelectMultipleField'):
            css_class = 'form-select'
        elif field_type in ('RadioField', 'CheckboxField'):
            css_class = ''
            options.setdefault('widget', CheckboxListWidget())
        else:
            css_class = 'form-control'

        if (extra := render_kw.get('class')):
            css_class = f'{css_class} {extra}' if css_class else extra

        render_kw['class'] = css_class
        options['render_kw'] = render_kw
        field = unbound_field.bind(form=form, **options)
        field.post_validate = partial(
            update_field_class,
            field,
            field.post_validate
        )
        if not isinstance(field, TransparentFormField):
            field.label = BootstrapLabel(field.label, field.description)
        return field

    def render_field(
            self,
            field: 'Field',
            render_kw: 'SupportsItems[str, Any]'
    ) -> 'Markup':

        # HACK: Immutable validators are special in that their field_flags
        #       should always be forwarded to render_kw, regardless of the
        #       field.
        flags = {}
        for validator in field.validators:
            if isinstance(validator, Immutable):
                flags.update(validator.field_flags)

        if flags:
            _render_kw = dict(render_kw.items())
            _render_kw.update(flags)
            render_kw = _render_kw
        return super().render_field(field, render_kw)

    # NOTE: We implement this so we can provide translations for the
    #       errors from the wtforms builtin validators
    def get_translations(self, form: '_BaseForm') -> PyramidTranslations:
        return PyramidTranslations()


class BootstrapLabel(Label):

    def __init__(self, base_label: Label, description: str):
        self.field_id = base_label.field_id
        self.text = base_label.text
        self.description = description

    def __call__(self, text: str | None = None, **kwargs: Any) -> 'Markup':
        kwargs.setdefault('class', 'form-label')
        if self.description:
            kwargs.setdefault('title', self.description)
            kwargs.setdefault('data_bs_toggle', 'tooltip')
        return super().__call__(text=text, **kwargs)


class Form(BaseForm):
    """ Base class for all forms in privatim. """

    Meta = BootstrapMeta

    def process(
            self,
            formdata:      '_MultiDictLike | None' = None,
            obj:           object | None = None,
            data:          'Mapping[str, Any] | None' = None,
            extra_filters: 'Mapping[str, Sequence[Any]] | None' = None,
            **kwargs: Any
    ) -> None:

        formdata = self.meta.wrap_formdata(self, formdata)

        if data is not None:
            kwargs = dict(data, **kwargs)

        for name, field, in self._fields.items():
            if isinstance(field, TransparentFormField):
                # NOTE: Treat the subform transparently with no prefix
                #       and the same object/field access
                field.form = field.form_class(
                    formdata=formdata,
                    obj=obj,
                    data=data,
                    **kwargs
                )
            elif obj is not None and hasattr(obj, name):
                field.process(formdata, getattr(obj, name))
            elif name in kwargs:
                field.process(formdata, kwargs[name])
            else:
                field.process(formdata)

    def populate_obj(self, obj: object) -> None:
        for name, field in self._fields.items():
            # don't populate disabled/read only fields
            if any(isinstance(v, Immutable) for v in field.validators or ()):
                continue

            field.populate_obj(obj, name)
