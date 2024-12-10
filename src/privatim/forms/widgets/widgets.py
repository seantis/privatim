import humanize
from contextlib import suppress
from markupsafe import Markup
from privatim.i18n import _, translate
from wtforms.widgets import FileInput

from typing import Any, TYPE_CHECKING
if TYPE_CHECKING:
    from privatim.forms.fields import (
        UploadField,
        UploadMultipleField,
    )


class UploadWidget(FileInput):
    """ An upload widget for the UploadField class, which supports keeping,
    removing and replacing already uploaded files.

    This is necessary as file inputs are read-only on the client and it's
    therefore rather easy for users to lose their input otherwise (e.g. a
    form with a file is rejected because of some mistake - the file disappears
    once the response is rendered on the client).

    """

    simple_template = Markup("""
        <div class="upload-widget without-data{wrapper_css_class}">
            {input_html}
        </div>
    """)
    template = Markup("""
        <div class="upload-widget with-data{wrapper_css_class}">
                <p class="file-title">
                    <b>
                        {existing_file_label}: {filename}{filesize} {icon}
                    </b>
                </p>

            {preview}

            <ul>
                <li>
                    <input type="radio" id="{name}-0" name="{name}"
                           value="keep" checked="">
                    <label for="{name}-0">{keep_label}</label>
                </li>
                <li>
                    <input type="radio" id="{name}-1" name="{name}"
                           value="delete">
                    <label for="{name}-1">{delete_label}</label>
                </li>
                <li>
                    <input type="radio" id="{name}-2" name="{name}"
                           value="replace">
                    <label for="{name}-2">{replace_label}</label>
                    <div>
                        <label>
                            <div data-depends-on="{name}/replace"
                                 data-hide-label="false">
                                {input_html}
                            </div>
                        </label>
                    </div>
                </li>
            </ul>

            {previous}
        </div>
    """)

    def image_source(self, field: 'UploadField') -> str | None:
        """ Returns the image source url if the field points to an image and
        if it can be done (it looks like it's possible, but I'm not super
        sure this is always possible).

        """

        if not hasattr(field.meta, 'request'):
            return None

        if not field.data:
            return None

        from privatim.forms.fields import IMAGE_MIME  # type:ignore
        if field.data.get('mimetype', None) not in IMAGE_MIME:
            return None

        if not hasattr(field, 'object_data'):
            return None

        if not field.object_data:
            return None

        with suppress(AttributeError):
            return field.meta.request.link(field.object_data)
        return None

    def template_data(
            self,
            field: 'UploadField',
            force_simple: bool,
            resend_upload: bool,
            wrapper_css_class: str,
            input_html: Markup,
            **kwargs: Any
    ) -> tuple[bool, dict[str, Any]]:

        if force_simple or field.errors or not field.data:
            return True, {
                'wrapper_css_class': wrapper_css_class,
                'input_html': input_html,
            }

        preview = ''
        src = self.image_source(field)
        if src:
            preview = Markup("""
                <div class="uploaded-image"><img src="{src}"></div>
            """).format(src=src)

        previous = ''
        if field.data and resend_upload:
            previous = Markup("""
                <input type="hidden" name="{name}" value="{filename}">
                <input type="hidden" name="{name}" value="{data}">
            """).format(
                name=field.id,
                filename=field.data.get('filename', ''),
                data=field.data.get('data', ''),
            )
        size = field.data['size']
        if size < 0:
            display_size = ''
        else:
            display_size = f' ({humanize.naturalsize(size)})'

        return False, {
            'wrapper_css_class': wrapper_css_class,
            'icon': '✓',
            'preview': preview,
            'previous': previous,
            'filesize': display_size,
            'filename': field.data['filename'],
            'name': field.id,
            'input_html': input_html,
            'existing_file_label': translate(_('Uploaded file')),
            'keep_label': translate(_('Keep file')),
            'delete_label': translate(_('Delete file')),
            'replace_label': translate(_('Replace file')),
        }

    def __call__(
            self,
            field: 'UploadField',  # type:ignore[override]
            **kwargs: Any
    ) -> Markup:

        force_simple = kwargs.pop('force_simple', False)
        resend_upload = kwargs.pop('resend_upload', False)
        wrapper_css_class = kwargs.pop('wrapper_css_class', '')
        if wrapper_css_class:
            wrapper_css_class = ' ' + wrapper_css_class
        input_html = super().__call__(field, **kwargs)

        is_simple, data = self.template_data(
            field,
            force_simple=force_simple,
            resend_upload=resend_upload,
            wrapper_css_class=wrapper_css_class,
            input_html=input_html,
            **kwargs
        )
        if is_simple:
            return self.simple_template.format(**data)
        return self.template.format(**data)


class UploadMultipleWidget(FileInput):
    """ A widget for the UploadMultipleField class, which supports keeping,
    removing and replacing already uploaded files.

    This is necessary as file inputs are read-only on the client and it's
    therefore rather easy for users to lose their input otherwise (e.g. a
    form with a file is rejected because of some mistake - the file disappears
    once the response is rendered on the client).

    We deviate slightly from the norm by rendering the errors ourselves
    since we're essentially a list of fields and not a single field most
    of the time.

    """

    additional_label = _('Upload additional files')

    def __init__(self) -> None:
        self.multiple = True

    def render_input(
            self,
            field: 'UploadMultipleField',
            **kwargs: Any
    ) -> Markup:
        return super().__call__(field, **kwargs)

    def __call__(
            self,
            field: 'UploadMultipleField',  # type:ignore[override]
            **kwargs: Any
    ) -> Markup:

        force_simple = kwargs.pop('force_simple', False)
        resend_upload = kwargs.pop('resend_upload', False)
        input_html = self.render_input(field, **kwargs)
        simple_template = Markup("""
            <div class="upload-widget without-data">
                {}
            </div>
        """)

        if force_simple or len(field) == 0:
            return simple_template.format(input_html)
        else:
            existing_html = Markup('').join(
                subfield(
                    force_simple=force_simple,
                    resend_upload=resend_upload,
                    wrapper_css_class='error' if subfield.errors else '',
                    **kwargs
                ) + Markup('\n').join(
                    Markup('<small class="error">{}</small>').format(error)
                    for error in subfield.errors
                ) for subfield in field
            )
            additional_html = Markup(
                '<label>{label}: {input_html}</label>'
            ).format(
                label=field.gettext(self.additional_label),
                input_html=input_html
            )
            return existing_html + simple_template.format(additional_html)
