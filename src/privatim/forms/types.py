from typing import TypeVar, TYPE_CHECKING, Any
from wtforms.form import BaseForm

FormT = TypeVar('FormT', bound='BaseForm', contravariant=True)
FieldT = TypeVar('FieldT', bound='Field', contravariant=True)

if TYPE_CHECKING:

    from typing import Protocol, TypeVar
    from typing_extensions import TypeAlias
    from webob.request import _FieldStorageWithFile
    from wtforms.fields.core import _Filter, _Validator, _Widget, Field

    _BaseFormT = TypeVar('_BaseFormT', bound=BaseForm, contravariant=True)
    _FormT = TypeVar('_FormT', bound=BaseForm, contravariant=True)
    _FieldT = TypeVar('_FieldT', bound=Field, contravariant=True)

    class FieldCondition(Protocol[_BaseFormT, _FieldT]):
        def __call__(self, __form: _BaseFormT, __field: _FieldT) -> bool: ...

    Widget: TypeAlias = _Widget
    Filter: TypeAlias = _Filter
    BaseValidator: TypeAlias = _Validator
    Validator: TypeAlias = _Validator[FormT, FieldT]
    Validators: TypeAlias = tuple[_Validator[FormT, FieldT], ...] | list[Any]
    # this matches what webob.request.POST returns as value type
    RawFormValue: TypeAlias = str | _FieldStorageWithFile
