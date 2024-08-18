from pyramid.httpexceptions import HTTPFound
from sqlalchemy import select
from webob.multidict import MultiDict

from privatim.forms.consultation_form import STATUS_CHOICES
from privatim.models import Consultation, User, Tag
from privatim.models.consultation import Status
from privatim.testing import DummyRequest
from privatim.views import edit_consultation_view


def test_edit_consultation_view_html_sanitization(pg_config):

    def get_status_label(status_code):
        for code, label in STATUS_CHOICES:
            if code == status_code:
                return label

    pg_config.add_route('activities', '/activities')
    pg_config.add_route('consultation', '/consultations/{id}/')
    pg_config.add_route('edit_consultation', '/consultations/{id}/edit')
    session = pg_config.dbsession

    user = User(email='testuser@example.org')
    tags = [
        Tag(name='SZ'),
        Tag(name='AG'),
    ]
    status = Status(name='Open')
    previous_consultation = Consultation(
        title='Test Consultation',
        description='This is a test consultation',
        recommendation='Some recommendation',
        status=status,
        secondary_tags=tags,
        creator=user
    )
    session.add_all([*tags, status, previous_consultation])

    session.add(previous_consultation)
    session.flush()

    dummy_request = DummyRequest(
        post=MultiDict(
            [
                ('csrf_token', 'e9af8a15fbf97fcba639d2c09d5049917e66e7ed'),
                ('title', 'Lorem ipsum dolor sit amet'),
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

    # Call the view
    response = edit_consultation_view(previous_consultation, dummy_request)

    # Check that it's a redirect (successful form submission)
    assert isinstance(response, HTTPFound)

    # Fetch the new consultation from the database
    new_consultation = session.scalars(
        select(Consultation).where(
            Consultation.title == 'Lorem ipsum dolor sit amet'
        )
    ).first()

    assert new_consultation.is_latest_version == 1
    assert new_consultation.description == '<p>s</p>'
    assert new_consultation.recommendation == '<img src="x">s'
    assert new_consultation.evaluation_result == '<a>f</a>'
    assert new_consultation.decision == ('&lt;style&gt;body { display: none; '
                                         '}&lt;/style&gt;Decision')
    assert new_consultation.status.name == get_status_label('2')

    tags_names = sorted([s.name for s in new_consultation.secondary_tags])
    assert tags_names == sorted(['AR', 'BE', 'BL'])

    # Check that the previous consultation has been updated
    assert previous_consultation.is_latest_version == 0
    assert previous_consultation.replaced_by == new_consultation
