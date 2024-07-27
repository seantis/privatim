import hashlib
from datetime import datetime
from typing import TYPE_CHECKING, Any

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


class Bunch:
    """ A simple but handy "collector of a bunch of named stuff" class.

    See `<https://code.activestate.com/recipes/\
    52308-the-simple-but-handy-collector-of-a-bunch-of-named/>`_.

    For example::

        point = Bunch(x=1, y=2)
        assert point.x == 1
        assert point.y == 2

        point.z = 3
        assert point.z == 3

    Allows the creation of simple nested bunches, for example::

        request = Bunch(**{'app.settings.org.my_setting': True})
        assert request.app.settings.org.my_setting is True

    """
    def __init__(self, **kwargs: Any):
        self.__dict__.update(
            (key, value)
            for key, value in kwargs.items()
            if '.' not in key
        )
        for key, value in kwargs.items():
            if '.' in key:
                name, _, key = key.partition('.')
                setattr(self, name, Bunch(**{key: value}))

    if TYPE_CHECKING:
        # let mypy know that any attribute access could be valid
        def __getattr__(self, name: str) -> Any: ...
        def __setattr__(self, name: str, value: Any) -> None: ...
        def __delattr__(self, name: str) -> None: ...

    def __eq__(self, other: object) -> bool:
        if type(other) is type(self):
            return self.__dict__ == other.__dict__
        return False

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)


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


def hash_file(file_bytes: bytes, hash_algorithm: str = 'sha256') -> str:
    hash_func = hashlib.new(hash_algorithm)
    hash_func.update(file_bytes)
    return hash_func.hexdigest()
