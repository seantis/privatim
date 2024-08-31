import inspect
from itertools import zip_longest
import sedate
from sqlalchemy import select

from privatim.models.file import SearchableFile
from privatim.static import tom_select_js
from wtforms.utils import unset_value
from wtforms.validators import DataRequired
from wtforms.validators import InputRequired
from wtforms.fields import FieldList
from wtforms.fields.choices import SelectMultipleField
from wtforms.fields.simple import FileField, TextAreaField
from wtforms.widgets.core import Select
from werkzeug.datastructures import MultiDict
from privatim.forms.widgets.widgets import UploadWidget, UploadMultipleWidget
from privatim.i18n import _

from wtforms.fields import DateTimeLocalField as DateTimeLocalFieldBase
from privatim.models.file import GeneralFile
from operator import itemgetter


from typing import Any, IO, Literal, TYPE_CHECKING, TypedDict
if TYPE_CHECKING:
    from markupsafe import Markup
    from sqlalchemy.orm import Session
    from wtforms.fields.choices import SelectFieldBase
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


__all__ = [
    "TomSelectWidget",
    "DateTimeLocalField",
    "TimezoneDateTimeField",
    "UploadField",
    "UploadMultipleField",
    # "UploadFileWithORMSupport",
    # "UploadMultipleFilesWithORMSupport",
    # "UploadOrLinkExistingFileField",
    # "UploadOrSelectExistingFileField",
    # "UploadOrSelectExistingMultipleFilesField"
]


def file_choices_from_session(session: 'Session') -> list[tuple[str, str]]:
    stmt = select(GeneralFile.id, GeneralFile.filename)
    result = session.execute(stmt)
    return sorted(
        ((file_id, name) for file_id, name in result),
        key=itemgetter(1),
    )


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


class ConstantTextAreaField(TextAreaField):
    """ TextAreaField that remains and will not be replaced by editor."""
    pass


class TomSelectWidget(Select):

    def __init__(
        self,
        multiple: bool = False,
    ) -> None:
        super().__init__(multiple=multiple)

    def __call__(self, field: 'SelectFieldBase', **kwargs: Any) -> 'Markup':
        if not kwargs.get('class'):
            kwargs['class'] = 'searchable-select'
        else:
            kwargs['class'] += ' searchable-select'

        placeholder = _('Select...')
        kwargs['placeholder_'] = placeholder
        kwargs['autocomplete_'] = 'off'
        return super(TomSelectWidget, self).__call__(field, **kwargs)


class SearchableMultiSelectField(SelectMultipleField):
    """
    A multiple select field with tom-select.js support.

    Note: This is unrelated to PostgreSQL full-text search, which also uses
    the term 'searchable'.
    Note: you need to call form.raw_data() to actually get the choices as list
    """

    def __init__(
        self,
        label: str,
        **kwargs: Any
    ):
        super().__init__(label, **kwargs)
        self.widget = TomSelectWidget(multiple=True)

    def __call__(self, **kwargs: Any) -> Any:
        tom_select_js.need()
        return super().__call__(**kwargs)


class SearchableSelectField(SelectMultipleField):
    """
    A select field with tom-select.js support.
    """

    def __init__(
            self,
            label: str,
            **kwargs: Any
    ):
        super().__init__(label, **kwargs)
        self.widget = TomSelectWidget(
            multiple=False
        )

    def __call__(self, **kwargs: Any) -> Any:
        tom_select_js.need()
        return super().__call__(**kwargs)


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

    def process_formdata(self, valuelist: list['RawFormValue']) -> None:

        if not valuelist:
            self.data = {}
            return

        from privatim.utils import binary_to_dictionary
        from privatim.utils import dictionary_to_binary

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
        self, field_storage: 'RawFormValue'
    ) -> 'StrictFileDict | FileDict':

        from privatim.utils import (
            binary_to_dictionary,
            path_to_filename,
        )
        self.file = getattr(
            field_storage, 'file', getattr(field_storage, 'stream', None)
        )
        self.filename = path_to_filename(getattr(field_storage,
                                                 'filename', None))

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
    upload_widget: 'Widget[UploadField]' = UploadWidget()

    def __init__(
        self,
        label: str | None = None,
        validators: 'Validators[_FormT, UploadField] | None' = None,
        filters: 'Sequence[Filter]' = (),
        description: str = '',
        id: str | None = None,
        default: 'Sequence[FileDict]' = (),
        widget: 'Widget[Self] | None' = None,
        render_kw: dict[str, Any] | None = None,
        name: str | None = None,
        upload_widget: 'Widget[UploadField] | None' = None,
        _form: 'BaseForm | None' = None,
        _prefix: str = '',
        _translations: '_SupportsGettextAndNgettext | None' = None,
        _meta: 'DefaultMeta | None' = None,
        **extra_arguments: Any
    ):
        if upload_widget is None:
            upload_widget = self.upload_widget

        # a lot of the arguments we just pass through to the subfield
        unbound_field = self.upload_field_class(
            validators=validators,
            filters=filters,
            description=description,
            widget=upload_widget,
            render_kw=render_kw,
            **extra_arguments)
        super().__init__(
            unbound_field,
            label,
            min_entries=0,
            max_entries=None,
            id=id,
            default=default,
            widget=widget,  # type:ignore[arg-type]
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


class _DummyFile:
    file: SearchableFile | None


class UploadFileWithORMSupport(UploadField):
    """ Extends the upload field with file support. """

    file_class: type[SearchableFile]

    def __init__(self, *args: Any, **kwargs: Any):
        self.file_class = kwargs.pop('file_class')
        super().__init__(*args, **kwargs)

    def create(self) -> SearchableFile | None:
        if not getattr(self, 'file', None):
            return None

        assert self.file is not None
        self.file.seek(0)
        assert self.filename is not None

        return SearchableFile(
            filename=self.filename,
            content=self.file.read(),
            content_type=self.data['mimetype'] if self.data else None,
        )

    def populate_obj(self, obj: object, name: str) -> None:

        # this is called upon form submission. So inserting the file works
        if not getattr(self, 'action', None):
            return

        if self.action == 'keep':
            pass

        elif self.action == 'delete':
            setattr(obj, name, None)

        elif self.action == 'replace':
            setattr(obj, name, self.create())

        else:
            raise NotImplementedError(f"Unknown action: {self.action}")

    def process_data(self, value: SearchableFile | None) -> None:

        if value:
            try:
                size = value.file.size
            except IOError:
                # if the file doesn't exist on disk we try to fail
                # silently for now
                size = -1
            self.data = {
                'filename': value.filename,
                'size': size,
                'mimetype': value.file.content_type
            }
        else:
            super().process_data(value)


class UploadMultipleFilesWithORMSupport(UploadMultipleField):
    """ Extends the upload multiple field with file support. """

    file_class: type[SearchableFile]
    added_files: list[SearchableFile]
    upload_field_class = UploadFileWithORMSupport

    def __init__(self, *args: Any, **kwargs: Any):
        self.file_class = kwargs['file_class']
        super().__init__(*args, **kwargs)

    def populate_obj(self, obj: object, name: str) -> None:
        self.added_files = []
        files = getattr(obj, name, ())
        output: list[SearchableFile] = []
        print(self.entries)

        for field, file in zip_longest(self.entries, files):
            if field is None:
                # breakpoint()
                # this generally shouldn't happen, but we should
                # guard against it anyways, since it can happen
                # if people manually call pop_entry()
                break

            dummy = _DummyFile()
            dummy.file = file
            field.populate_obj(dummy, 'file')
            if dummy.file is not None:
                output.append(dummy.file)
                if (
                    dummy.file is not file
                    # an upload field may mark a file as having already
                    # existed previously, in this case we don't consider
                    # it having being added
                    and getattr(field, 'existing_file', None) is None
                ):
                    # added file
                    self.added_files.append(dummy.file)

        setattr(obj, name, output)
