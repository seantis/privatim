from __future__ import annotations
from typing import TypeVar, TYPE_CHECKING, Any
from wtforms.form import BaseForm

BaseFormT = TypeVar('BaseFormT', bound='BaseForm', contravariant=True)
FormT = TypeVar('FormT', bound='BaseForm', contravariant=True)
FieldT = TypeVar('FieldT', bound='Field', contravariant=True)

if TYPE_CHECKING:

    from typing import Protocol, TypeVar
    from typing import TypeAlias
    from webob.request import _FieldStorageWithFile
    from wtforms.fields.core import _Filter, _Validator, _Widget, Field

    class FieldCondition(Protocol[BaseFormT, FieldT]):
        def __call__(self, form: BaseFormT, field: FieldT, /) -> bool: ...

    Widget: TypeAlias = _Widget
    Filter: TypeAlias = _Filter
    BaseValidator: TypeAlias = _Validator
    Validator: TypeAlias = _Validator[FormT, FieldT]
    Validators: TypeAlias = tuple[_Validator[FormT, FieldT], ...] | list[Any]
    # this matches what webob.request.POST returns as value type
    RawFormValue: TypeAlias = str | _FieldStorageWithFile
