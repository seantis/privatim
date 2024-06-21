import inspect
import sedate
from privatim.static import init_tom_select
from wtforms.utils import unset_value
from wtforms.validators import DataRequired
from wtforms.validators import InputRequired
from wtforms.fields import FieldList
from wtforms.fields.choices import SelectField
from wtforms.fields.simple import FileField
from wtforms.widgets.core import Select
from werkzeug.datastructures import MultiDict
from privatim.forms.widgets.widgets import UploadWidget, UploadMultipleWidget
from privatim.i18n import _
from privatim.utils import (
    binary_to_dictionary,
    dictionary_to_binary,
    path_to_filename,
    get_supported_image_mime_types,
)
from wtforms.fields import DateTimeLocalField as DateTimeLocalFieldBase


from typing import Any, IO, Literal, TYPE_CHECKING, TypedDict
if TYPE_CHECKING:
    from wtforms.fields.choices import SelectFieldBase
    from markupsafe import Markup
    from collections.abc import Sequence
    from datetime import datetime
    from privatim.types import FileDict as StrictFileDict
    from privatim.forms.types import (
        _FormT,
        Filter,
        RawFormValue,
        Validators,
        Widget,
    )
    from typing_extensions import Self
    from webob.request import _FieldStorageWithFile
    from wtforms.form import BaseForm
    from wtforms.meta import (
        _MultiDictLikeWithGetlist,
        _SupportsGettextAndNgettext,
        DefaultMeta,
    )

    class FileDict(TypedDict, total=False):
        data: str
        filename: str | None
        mimetype: str
        size: int

    # this is only generic at type checking time
    class UploadMultipleBase(FieldList['UploadField']):
        pass

else:
    UploadMultipleBase = FieldList


EXCLUDED_IMAGE_TYPES = {'application/pdf'}
IMAGE_MIME_TYPES = get_supported_image_mime_types() - EXCLUDED_IMAGE_TYPES
IMAGE_MIME = IMAGE_MIME_TYPES | {'image/svg+xml'}


__all__ = [
    "ChosenSelectWidget",
    "DateTimeLocalField",
    "TimezoneDateTimeField",
    "SearchableSelectField",
    "UploadField",
    "UploadMultipleField",
]


class ChosenSelectWidget(Select):

    def __call__(self, field: 'SelectFieldBase', **kwargs: Any) -> 'Markup':
        if not kwargs.get('class'):
            kwargs['class'] = 'searchable-select'
        else:
            kwargs['class'] += ' searchable-select'
        kwargs['placeholder_'] = _('Select...')
        kwargs['autocomplete_'] = 'off'
        return super(ChosenSelectWidget, self).__call__(field, **kwargs)


class DateTimeLocalField(DateTimeLocalFieldBase):
    """ A custom implementation of the DateTimeLocalField to fix issues with
    the format and the datetimepicker plugin.

    """

    def __init__(
            self,
            label: str | None = None,
            validators: 'Validators[_FormT, Self] | None' = None,
            format: str = '%Y-%m-%dT%H:%M',
            **kwargs: Any
    ):
        super(DateTimeLocalField, self).__init__(
            label=label,
            validators=validators,
            format=format,
            **kwargs
        )

    def process_formdata(self, valuelist: list['RawFormValue']) -> None:
        if valuelist:
            date_str = 'T'.join(valuelist).replace(' ', 'T')  # type:ignore
            valuelist = [date_str[:16]]
        super(DateTimeLocalField, self).process_formdata(valuelist)


class TimezoneDateTimeField(DateTimeLocalField):
    """ A datetime field data returns the date with the given timezone
    and expects datetime values with a timezone.

    """

    data: 'datetime | None'

    def __init__(self, *args: Any, timezone: str, **kwargs: Any):
        self.timezone = timezone
        super().__init__(*args, **kwargs)

    def process_data(self, value: 'datetime | None') -> None:
        if value:
            value = sedate.to_timezone(value, self.timezone)
            value.replace(tzinfo=None)

        super().process_data(value)

    def process_formdata(self, valuelist: list['RawFormValue']) -> None:
        super().process_formdata(valuelist)

        if self.data:
            self.data = sedate.replace_timezone(self.data, self.timezone)


class SearchableSelectField(SelectField):
    """A multiple select field with tom-select.js support.

    Note: you need to call form.raw_data() to actually get the choices as list
    """

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        init_tom_select.need()
        return super().__call__(*args, **kwargs)

    widget = ChosenSelectWidget(multiple=True)


class UploadField(FileField):
    """A custom file field that turns the uploaded file into a compressed
    base64 string together with the filename, size and mimetype.

    """

    widget = UploadWidget()
    action: Literal['keep', 'replace', 'delete']
    file: IO[bytes] | None
    filename: str | None

    # this is not quite accurate, since it is either a dictionary with all
    # the keys or none of the keys, which would make type narrowing easier
    # unfortunately a union of two TypedDict will narrow to the TypedDict
    # with the fewest shared keys, which would always be an empty dictionary
    @property
    def data(self) -> 'StrictFileDict | FileDict | None':
        frame = inspect.currentframe()
        assert frame is not None and frame.f_back is not None
        caller = frame.f_back.f_locals.get('self')

        # give the required validators the idea that the data is there
        # when the action was to keep the current file - an evil approach
        if isinstance(caller, (DataRequired, InputRequired)):
            truthy = (
                getattr(self, '_data', None)
                or getattr(self, 'action', None) == 'keep'
            )

            return truthy  # type:ignore[return-value]

        return getattr(self, '_data', None)

    @data.setter
    def data(self, value: 'FileDict') -> None:
        self._data = value

    @property
    def is_image(self) -> bool:
        if not self.data:
            return False
        return self.data.get('mimetype') in IMAGE_MIME

    def process_formdata(self, valuelist: list['RawFormValue']) -> None:

        if not valuelist:
            self.data = {}
            return

        fieldstorage: RawFormValue
        action: RawFormValue
        if len(valuelist) == 4:
            # resend_upload
            action = valuelist[0]
            fieldstorage = valuelist[1]
            self.data = binary_to_dictionary(
                dictionary_to_binary({'data': str(valuelist[3])}),
                str(valuelist[2]),
            )
        elif len(valuelist) == 2:
            # force_simple
            action, fieldstorage = valuelist
        else:
            # default
            action = 'replace'
            fieldstorage = valuelist[0]

        if action == 'replace':
            self.action = 'replace'
            self.data = self.process_fieldstorage(fieldstorage)
        elif action == 'delete':
            self.action = 'delete'
            self.data = {}
        elif action == 'keep':
            self.action = 'keep'
        else:
            raise NotImplementedError()

    def process_fieldstorage(
        self, fs: 'RawFormValue'
    ) -> 'StrictFileDict | FileDict':

        self.file = getattr(fs, 'file', getattr(fs, 'stream', None))
        self.filename = path_to_filename(getattr(fs, 'filename', None))

        if not self.file:
            return {}

        self.file.seek(0)

        try:
            return binary_to_dictionary(self.file.read(), self.filename)
        finally:
            self.file.seek(0)


class UploadMultipleField(UploadMultipleBase, FileField):
    """A custom file field that turns the uploaded files into a list of
    compressed base64 strings together with the filename, size and mimetype.

    This acts both like a single file field with multiple and like a list
    of UploadFile for uploaded files. This way
    we get the best of both worlds.

    """

    widget = UploadMultipleWidget()
    raw_data: list['RawFormValue']

    if TYPE_CHECKING:
        _separator: str

        def _add_entry(
            self, __d: _MultiDictLikeWithGetlist
        ) -> UploadField: ...

    upload_field_class: type[UploadField] = UploadField
    upload_widget: 'Widget[UploadField]' = UploadWidget()  # type:ignore

    def __init__(
        self,
        label: str | None = None,
        validators: 'Validators[_FormT, UploadField] | None' = None,
        filters: 'Sequence[Filter]' = (),
        description: str = '',
        id: str | None = None,
        default: 'Sequence[FileDict]' = (),
        widget: 'Widget[Self] | None' = None,  # type:ignore
        render_kw: dict[str, Any] | None = None,
        name: str | None = None,
        upload_widget: 'Widget[UploadField] | None' = None,  # type:ignore
        _form: 'BaseForm | None' = None,
        _prefix: str = '',
        _translations: '_SupportsGettextAndNgettext | None' = None,
        _meta: 'DefaultMeta | None' = None,
    ):
        if upload_widget is None:
            upload_widget = self.upload_widget

        # a lot of the arguments we just pass through to the subfield
        unbound_field = self.upload_field_class(
            validators=validators,
            filters=filters,
            description=description,
            widget=upload_widget,
        )
        super().__init__(
            unbound_field,
            label,
            min_entries=0,
            max_entries=None,
            id=id,
            default=default,
            widget=widget,
            render_kw=render_kw,
            name=name,
            _form=_form,
            _prefix=_prefix,
            _translations=_translations,
            _meta=_meta,
        )

    def __bool__(self) -> Literal[True]:
        # because FieldList implements __len__ this field would evaluate
        # to False if no files have been uploaded, which is not generally
        # what we want
        return True

    def process(
        self,
        formdata: '_MultiDictLikeWithGetlist | None',
        data: object = unset_value,
        extra_filters: 'Sequence[Filter] | None' = None,
    ) -> None:
        self.process_errors = []

        # process the sub-fields
        super().process(formdata, data=data, extra_filters=extra_filters)

        # process the top-level multiple file field
        if formdata is not None:
            if self.name in formdata:
                self.raw_data = formdata.getlist(self.name)
            else:
                self.raw_data = []

            try:
                self.process_formdata(self.raw_data)
            except ValueError as e:
                self.process_errors.append(e.args[0])

    def process_formdata(self, valuelist: list['RawFormValue']) -> None:
        if not valuelist:
            return

        # only create entries for valid field storage
        for value in valuelist:
            if isinstance(value, str):
                continue

            if hasattr(value, 'file') or hasattr(value, 'stream'):
                self.append_entry_from_field_storage(value)

    def append_entry_from_field_storage(
        self, fs: '_FieldStorageWithFile'
    ) -> UploadField:
        # we fake the formdata for the new field
        # we use a werkzeug MultiDict because the WebOb version
        # needs to get wrapped to be usable in WTForms
        formdata: MultiDict[str, RawFormValue] = MultiDict()
        name = f'{self.short_name}{self._separator}{len(self)}'
        formdata.add(name, fs)
        return self._add_entry(formdata)
