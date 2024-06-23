import inspect
from itertools import zip_longest

import sedate
from sqlalchemy import select
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
from privatim.models import GeneralFile
from operator import itemgetter


from typing import Any, IO, Literal, TYPE_CHECKING, TypedDict
if TYPE_CHECKING:
    from sqlalchemy.orm import Session
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
        formdata: MultiDict[str, 'RawFormValue'] = MultiDict()
        name = f'{self.short_name}{self._separator}{len(self)}'
        formdata.add(name, fs)
        return self._add_entry(formdata)


class _DummyFile:
    file: GeneralFile | None


class UploadFileWithORMSupport(UploadField):
    """ Extends the upload field with onegov.file support. """

    file_class: type[GeneralFile]

    def __init__(self, *args: Any, **kwargs: Any):
        self.file_class = kwargs.pop('file_class')
        super().__init__(*args, **kwargs)

    def create(self) -> GeneralFile | None:
        if not getattr(self, 'file', None):
            return None

        assert self.file is not None
        self.file.seek(0)
        assert self.filename is not None
        return GeneralFile(filename=self.filename, content=self.file.read())

    def populate_obj(self, obj: object, name: str) -> None:

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

    def process_data(self, value: GeneralFile | None) -> None:

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
                'mimetype': value.content_type
            }
        else:
            super().process_data(value)


class UploadMultipleFilesWithORMSupport(UploadMultipleField):
    """ Extends the upload multiple field with file support. """

    file_class: type[GeneralFile]
    added_files: list[GeneralFile]
    upload_field_class = UploadFileWithORMSupport

    def __init__(self, *args: Any, **kwargs: Any):
        self.file_class = kwargs['file_class']
        super().__init__(*args, **kwargs)

    def populate_obj(self, obj: object, name: str) -> None:
        self.added_files = []
        files = getattr(obj, name, ())
        output: list[GeneralFile] = []
        print(self.entries)

        # for field, file in zip_longest(self.entries, files): print('l');
        for field, file in zip_longest(self.entries, files):
            print('l')
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

        # breakpoint()
        setattr(obj, name, output)
#
#
# class UploadOrLinkExistingFileField(UploadFileWithORMSupport):
#     """ An extension of :class:`onegov.form.fields.UploadFileWithORMSupport`
#     which will select existing uploaded files to link from a given
#     :class:`onegov.file.FileCollection` class in addition to uploading
#     new files.
#
#     This class is mostly useful in conjunction with
#     :class:`onegov.org.forms.fields.UploadOrSelectExistingMultipleFilesField`
#     if you want to link or upload only a single file, then you should
#     use :class:`onegov.org.forms.fields.UploadOrSelectExistingFileField`.
#
#     """
#
#     existing_file: GeneralFile | None
#     widget = UploadOrLinkExistingFileWidget()
#
#     def __init__(
#             self,
#             *args: Any,
#             **kwargs: Any
#     ) -> None:
#         # if we got this argument we discard it, we don't use it
#         kwargs.pop('_choices', None)
#
#         # we don't really use file_class since we use the collection
#         # to create the files instead
#         kwargs.setdefault('file_class', GeneralFile)
#         super().__init__(*args, **kwargs)
#
#         meta = kwargs.get('_meta') or kwargs['_form'].meta
#         if not hasattr(meta, 'dbsession'):
#             super().__init__(*args, **kwargs, file_class=GeneralFile)
#             return
#
#         self.session = meta.dbsession
#
#     def populate_obj(self, obj: object, name: str) -> None:
#         # shortcut for when a file was explicitly selected
#         existing = getattr(self, 'existing_file', None)
#         if existing is not None:
#             setattr(obj, name, existing)
#             return
#
#         super().populate_obj(obj, name)
#
#     def create(self) -> GeneralFile | None:
#         if not getattr(self, 'file', None):
#             return None
#
#         assert self.file is not None
#         self.file.seek(0)
#
#         file = GeneralFile(filename=self.filename, content=self.file.read())
#         self.session.add(file)
#         self.session.flush()
#         return file
#
#
# class UploadOrSelectExistingFileField(UploadOrLinkExistingFileField):
#     """ An extension of :class:`onegov.form.fields.UploadFileWithORMSupport`
#     to allow selecting existing uploaded files from a given
#     :class:`onegov.file.FileCollection` class in addition to uploading
#     new files.
#
#     :param file_collection:
#         The file collection class to use, should be a subclass of
#         :class:`onegov.file.FileCollection`.
#
#     :param file_type:
#         The polymorphic type to use and to filter for.
#
#     :param allow_duplicates:
#         Prevents duplicates if set to false. Rather than throw an error
#         it will link to the existing file and discard the new file.
#
#     """
#
#     widget = UploadOrSelectExistingFileWidget()
#
#     def __init__(
#             self,
#             *args: Any,
#             _choices: list[tuple[str, str]] | None = None,
#             **kwargs: Any
#     ):
#         super().__init__(
#             *args,
#             **kwargs
#         )
#
#         if _choices is None:
#             _choices = file_choices_from_session(self.session)
#         self.choices = _choices
#
#     def process_formdata(self, valuelist: list['RawFormValue']) -> None:
#
#         if not valuelist:
#             self.data = {}
#             return
#
#         fieldstorage: RawFormValue
#         action: RawFormValue
#         if len(valuelist) == 5:
#             # resend_upload
#             action = valuelist[0]
#             fieldstorage = valuelist[1]
#             existing = valuelist[2]
#             self.data = binary_to_dictionary(
#                 dictionary_to_binary({'data': str(valuelist[4])}),
#                 str(valuelist[3])
#             )
#         elif len(valuelist) == 3:
#             action, fieldstorage, existing = valuelist
#         else:
#             # default
#             action = 'replace'
#             fieldstorage = valuelist[0]
#
#         if action == 'replace':
#             self.action = 'replace'
#             self.data = self.process_fieldstorage(fieldstorage)
#             self.existing = None
#         elif action == 'delete':
#             self.action = 'delete'
#             self.data = {}
#             self.existing = None
#         elif action == 'keep':
#             self.action = 'keep'
#             self.existing = None
#         elif action == 'select':
#             self.action = 'replace'
#             if not isinstance(existing, str):
#                 self.existing = None
#                 return
#
#             if self.collection is None:
#                 self.collection = self.collection_class(  # type:ignore
#                     self.meta.request.session,
#                 )
#
#             self.existing = existing
#             self.existing_file = self.collection.by_id(existing)
#             self.process_data(self.existing_file)
#         else:
#             raise NotImplementedError()
#
#
# class UploadOrSelectExistingMultipleFilesField(
#     UploadMultipleFilesWithORMSupport
# ):
#     """ An extension of
#     :class:`onegov.form.fields.UploadMultipleFilesWithORMSupport` to
#     allow selecting existing uploaded files from a given
#     :class:`onegov.file.FileCollection` class in addition to uploading
#     new files.
#
#
#     """
#
#     widget = UploadOrSelectExistingMultipleFilesWidget()
#     upload_field_class = UploadOrLinkExistingFileField
#     upload_widget = UploadOrLinkExistingFileWidget()
#
#     def __init__(
#             self,
#             *args: Any,
#             **kwargs: Any
#     ):
#         meta = kwargs.get('_meta') or kwargs['_form'].meta
#         if not hasattr(meta, 'dbsession'):
#             super().__init__(*args, **kwargs, file_class=GeneralFile)
#             return
#         self.session = meta.dbsession
#         self.choices = file_choices_from_session(self.session)
#
#         super().__init__(
#             *args,
#             **kwargs,
#             file_class=GeneralFile,
#             _choices=self.choices,
#         )
#
#     def process_formdata(self, valuelist: list['RawFormValue']) -> None:
#         if not valuelist:
#             return
#
#         breakpoint()
#         for value in valuelist:
#             if isinstance(value, str):
#                 if any(f.id == value for f in self.object_data or ()):
#                     # if this file has already been added, then don't add
#                     # it again
#                     continue
#
#                 existing = self.session.query().filter(
#                 GeneralFile.id == value).first()
#                 if existing is not None:
#                     field = self.append_entry(existing)
#                     field.existing_file \
#                     = existing  # type:ignore[attr-defined]
#
#             elif hasattr(value, 'file') or hasattr(value, 'stream'):
#                 self.append_entry_from_field_storage(value)
