from datetime import datetime
from sedate import utcnow
from privatim.layouts.layout import DEFAULT_TIMEZONE
from privatim.models import (
    Meeting,
    WorkingGroup,
    User,
    ConsultationDocument,
    Tag,
    Consultation,
)
from privatim.models.consultation import Status


def find_login_form(resp_forms):
    """More than one form exists on the login page. Find the one we need"""
    for v in resp_forms.values():
        keys = v.fields.keys()
        if 'email' in keys and 'password' in keys:
            return v
    return None


def create_meeting(attendees=None) -> Meeting:
    """ Helper function to create a meeting with some attendees """
    attendees = attendees or [
        User(email='john@doe.org', first_name='John', last_name='Doe'),
        User(
            email='schabala@babala.ch',
            first_name='Schabala',
            last_name='Babala',
        ),
    ]
    return Meeting(
        name='Powerpoint Parade',
        time=datetime.now(tz=DEFAULT_TIMEZONE),
        attendees=attendees,
        working_group=WorkingGroup(
            name='Waffle Workshop Group', leader=attendees[0], users=attendees
        ),
    )


def create_consultation(documents=None, tags=None):

    documents = documents or [
        ConsultationDocument(
            name='document1.pdf',
            content=b'Content of Document 1',
        ),
        ConsultationDocument(
            name='document2.pdf',
            content=b'Content of Document 2',
        ),
    ]

    tags = tags or [
        Tag(name='SZ'),
        Tag(name='AG'),
    ]

    return Consultation(
        title='Test Consultation',
        description='This is a test consultation',
        recommendation='Some recommendation',
        status=Status(name='Open'),
        created=utcnow(),
        documents=documents,
        secondary_tags=tags,
    )
