from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from babel.dates import format_datetime
from privatim.i18n import translate, _
from privatim.layouts.layout import DEFAULT_TIMEZONE
from privatim.utils import datetime_format
from pyramid.renderers import render
from weasyprint import HTML, CSS  # type: ignore
from weasyprint.text.fonts import FontConfiguration  # type: ignore


from typing import TYPE_CHECKING, Protocol
if TYPE_CHECKING:
    from privatim.models import Meeting
    from pytz import BaseTzInfo
    from pyramid.interfaces import IRequest


@dataclass
class ReportOptions:

    language: str = 'de'
    """ Translate report into language. """

    tz: 'BaseTzInfo' = DEFAULT_TIMEZONE
    """ Use timezone for all timestamps. """


@dataclass
class PDFDocument:

    data: bytes
    """ Raw PDF content. """

    filename: str
    """ Document's filename when stored or downloaded. """


class ReportRenderer(Protocol):

    def render(
        self,
        meeting: 'Meeting',
        timestamp: str,
        request: 'IRequest'
    ) -> bytes:
        ...


class MeetingReport:

    def __init__(
            self,
            request: 'IRequest',
            meeting: 'Meeting',
            options: ReportOptions,
            renderer: ReportRenderer
    ) -> None:
        self.request = request
        self.meeting = meeting
        self.renderer = renderer
        self.issued_at = datetime.utcnow()
        self.options = options

    @property
    def created_at(self) -> str:
        """ Returns formatted report date.  """
        return format_datetime(
            self.issued_at,
            format='short',
            locale=self.options.language,
            tzinfo=self.options.tz
        ).replace('\u202f', ' ')

    @property
    def filename(self) -> str:
        datestr = format_datetime(
            self.issued_at,
            format='YYMMdd',
            locale=self.options.language,
            tzinfo=self.options.tz
        )
        return f'{datestr}_{self.meeting.name}.pdf'

    def build(self) -> PDFDocument:
        """ Render report as PDF.  """

        pdf = self.renderer.render(
            self.meeting,
            self.created_at,
            self.request
        )

        return PDFDocument(pdf, self.filename)


class HTMLReportRenderer:
    """
    Render meeting report with WeasyPrint, using HTML and CSS.
    You can turn on logging for weasyprint to debug issues:
        >>> import logging, sys
        >>> logger = logging.getLogger('weasyprint')
        >>> logger.setLevel(logging.DEBUG)
        >>> logger.addHandler(logging.StreamHandler(sys.stdout))
    """
    template = 'privatim:reporting/template/report.pt'

    def render(
            self,
            meeting: 'Meeting',
            timestamp: str,
            request: 'IRequest'
    ) -> bytes:
        html = self.render_template(meeting, timestamp, request)
        return self.render_pdf(html, request)

    def render_template(
            self,
            meeting: 'Meeting',
            timestamp: str,
            request: 'IRequest'
    ) -> str:
        """Render chameleon report template."""
        document_context = {'title': meeting.name, 'created_at': timestamp}
        title = translate(
            _(
                "Protocol of meeting ${title}",
                mapping={'title': document_context['title']},
            )
        )
        ctx = {
            'title': title,
            'meeting': meeting,
            'sorted_attendance_records': meeting.attendance_records,
            'meeting_time': datetime_format(meeting.time),
            'document': document_context,
        }
        return render(self.template, ctx)

    def render_pdf(self, html: str, request: 'IRequest') -> bytes:
        """
        Render processed chameleon template as PDF.
        """
        resource_base_url = Path.cwd() / 'privatim' / 'reporting'
        buffer = BytesIO()

        italic_font_name = 'dm-sans-v6-latin-ext_latin-500italic.woff'
        italic_font_name_woff2 = 'dm-sans-v6-latin-ext_latin-500italic.woff2'
        regular_font_name = 'dm-sans-v6-latin-ext_latin-500.woff'
        regular_font_name_woff2 = 'dm-sans-v6-latin-ext_latin-500.woff2'
        normal_font_name = 'dm-sans-v6-latin-ext_latin-regular.woff'
        normal_font_name_woff2 = 'dm-sans-v6-latin-ext_latin-regular.woff2'
        normal_italic_font_name = 'dm-sans-v6-latin-ext_latin-italic.woff'
        normal_italic_font_name_wo2 = 'dm-sans-v6-latin-ext_latin-italic.woff2'
        base_font_url = 'privatim:static/fonts/'

        # Create URLs first
        font_paths = {
            'regular': f'{base_font_url}{regular_font_name}',
            'regular_woff2': f'{base_font_url}{regular_font_name_woff2}',
            'italic': f'{base_font_url}{italic_font_name}',
            'italic_woff2': f'{base_font_url}{italic_font_name_woff2}',
            'normal': f'{base_font_url}{normal_font_name}',
            'normal_woff2': f'{base_font_url}{normal_font_name_woff2}',
            'normal_italic': f'{base_font_url}{normal_italic_font_name}',
            'normal_italic_woff2': f'{base_font_url}'
                                   f'{normal_italic_font_name_wo2}',
        }

        font_urls = {
            key: request.static_url(path) for key, path in font_paths.items()
        }

        font_config = FontConfiguration()
        css_font_face = f'''
        @font-face {{
            font-family: 'DM Sans';
            font-style: normal;
            font-weight: 400;
            src: url({font_urls['normal_woff2']}) format('woff2'),
                 url({font_urls['normal']}) format('woff');
        }}
        @font-face {{
            font-family: 'DM Sans';
            font-style: italic;
            font-weight: 400;
            src: url({font_urls['normal_italic_woff2']}) format('woff2'),
                 url({font_urls['normal_italic']}) format('woff');
        }}
        @font-face {{
            font-family: 'DM Sans';
            font-style: normal;
            font-weight: 500;
            src: url({font_urls['regular_woff2']}) format('woff2'),
                 url({font_urls['regular']}) format('woff');
        }}
        @font-face {{
            font-family: 'DM Sans';
            font-style: italic;
            font-weight: 500;
            src: url({font_urls['italic_woff2']}) format('woff2'),
                 url({font_urls['italic']}) format('woff');
        }}
        '''

        css = CSS(string=css_font_face, font_config=font_config)
        HTML(string=html, base_url=str(resource_base_url)).write_pdf(
            buffer,
            stylesheets=[css],
            font_config=font_config
        )
        return buffer.getvalue()
