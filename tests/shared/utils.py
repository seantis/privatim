from datetime import datetime
from typing import TYPE_CHECKING

from sedate import utcnow

from privatim.layouts.layout import DEFAULT_TIMEZONE
from privatim.models import (
    Meeting,
    WorkingGroup,
    User,
    Tag,
    Consultation,
    AgendaItem,
)
from privatim.models.consultation import Status
from privatim.models.file import SearchableFile
from privatim.testing import DummyRequest

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


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


def create_meeting_with_agenda_items(
    agenda_items: list[dict[str, str]], session: 'Session'
) -> Meeting:
    meeting = create_meeting()
    for item in agenda_items:
        AgendaItem.create(
            session,
            title=item['title'],
            description=item['description'],
            meeting=meeting,
        )
    session.add(meeting)
    session.flush()
    return meeting


def create_consultation(documents=None, tags=None, user=None):

    documents = documents or [
        SearchableFile(
            filename='document1.pdf',
            content=b'Content of Document 1',
        ),
        SearchableFile(
            filename='document2.pdf',
            content=b'Content of Document 2',
        ),
    ]
    user = user or User(email='testuser@example.org')
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
        files=documents,
        secondary_tags=tags,
        creator=user
    )


class CustomDummyRequest(DummyRequest):
    """ Make `static_url` work for the cases we need it to work."""
    def static_url(self, path: str) -> str:
        # Assuming the input path has a prefix "privatim:static/"
        prefix = 'privatim:static/'
        if path.startswith(prefix):
            path = path[len(prefix):]
        return f'{self.host}/static/{path}'
