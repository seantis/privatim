from markupsafe import Markup
from webob.multidict import MultiDict

from privatim.forms.consultation_form import ConsultationForm
from privatim.forms.core import HtmlField
from privatim.testing import DummyRequest


def test_html_cleaned(session):
    request = DummyRequest(
        post=MultiDict(
            [
                ('csrf_token', 'e9af8a15fbf97fcba639d2c09d5049917e66e7ed'),
                ('title', 'Lorem ipsum dolor sit amet,'),
                (
                    'description',
                    '<p onclick="alert(\'XSS\')">s</p>',
                ),
                (
                    'recommendation',
                    '<img src="x" onerror="alert(\'XSS\')">s',
                ),
                (
                    'evaluation_result',
                    '<a href="javascript:alert(' '\'XSS\')">f</a>',
                ),
                (
                    'decision',
                    '<style>body { display: none; }</style>Decision',
                ),
                ('status', '2'),
                ('secondary_tags', 'AR'),
                ('secondary_tags', 'BE'),
                ('secondary_tags', 'BL'),
            ]
        )
    )

    request.dbsession = session
    form = ConsultationForm(None, request)
    for f in form:
        if isinstance(f, HtmlField):
            f.pre_validate(form)

    assert form.data == {
        'title': 'Lorem ipsum dolor sit amet,',
        'description': Markup('<p>s</p>'),
        'recommendation': Markup('<img src="x">s'),
        'evaluation_result': Markup('<a>f</a>'),
        'decision': Markup(
            '&lt;style&gt;body { display: none; }&lt;/style&gt;Decision'
        ),
        'status': '2',
        'secondary_tags': ['AR', 'BE', 'BL'],
        'files': [],
    }
