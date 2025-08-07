import hashlib
import uuid
from datetime import datetime
from privatim.layouts.layout import DEFAULT_TIMEZONE
from privatim.models import (
    Meeting,
    WorkingGroup,
    User,
    Consultation,
    AgendaItem,
)
from privatim.models.file import SearchableFile
from privatim.testing import DummyRequest


from typing import TYPE_CHECKING, Any
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


def create_meeting(
    name: str | None = None,
    attendees: list[User] | None = None,
    files: list[SearchableFile] | None = None,
    creator: User | None = None,
    working_group: WorkingGroup | None = None,
) -> Meeting:
    """ Helper function to create a meeting with attendees and optional files.
    """
    if attendees is None:
        attendees = [
            User(email='john@doe.org', first_name='John', last_name='Doe'),
            User(
                email='schabala@babala.ch',
                first_name='Schabala',
                last_name='Babala',
            ),
        ]

    if working_group is None:
        working_group = WorkingGroup(
            name='Waffle Workshop Group',
            users=attendees
        )

    meeting = Meeting(
        name=name or 'Powerpoint Parade',
        time=datetime.now(tz=DEFAULT_TIMEZONE),
        attendees=attendees,
        working_group=working_group,
        creator=creator,
    )

    meeting.files = files or []
    return meeting


def create_meeting_with_agenda_items(
    agenda_items: list[dict[str, str]], session: 'Session'
) -> Meeting:
    meeting = create_meeting()
    for item in agenda_items:
        created_item = AgendaItem.create(
            session,
            title=item['title'],
            description=item['description'],
            meeting=meeting,
        )
        session.add(created_item)
    session.add(meeting)
    session.flush()
    return meeting


def create_consultation(
    title: str | None = None,
    status: str | None = None,
    documents=None,
    tags=None,
    user=None,
    previous_version=None,
):
    documents = documents or [
        SearchableFile(
            filename='document1.txt',
            content=b'Content of Document 1',
        ),
        SearchableFile(
            filename='document2.txt',
            content=b'Content of Document 2',
        ),
    ]

    # If no user is provided, create one. Be mindful of potential email clashes
    # in tests calling this multiple times without specifying a user.
    if user is None:
        # Use a more unique default
        user = User(email=f'consultation-creator-{uuid.uuid4()}@example.org')

    consultation = Consultation(
        title=title or 'Test Consultation',
        status=status,  # Pass status directly, Consultation handles default
        description='This is a test consultation',
        recommendation='Some recommendation',
        files=documents,
        secondary_tags=tags or ['SZ, AG'],
        creator=user,
        previous_version=previous_version,
    )
    return consultation


class CustomDummyRequest(DummyRequest):
    """ Make `static_url` work for the cases we need it to work."""
    def static_url(self, path: str) -> str:
        prefix = 'privatim:static/'
        if path.startswith(prefix):
            path = path[len(prefix):]
        return f'{self.host}/static/{path}'


def hash_file(file_bytes: bytes, hash_algorithm: str = 'sha256') -> str:
    hash_func = hashlib.new(hash_algorithm)
    hash_func.update(file_bytes)
    return hash_func.hexdigest()


def get_pre_filled_content_on_searchable_field(page, field_id):
    """
    Get a list of items that were pre-populated in the
    SearchableMultiSelectField.

    It accesses the 'options' list from the specific nested structure
    in form_fields."""
    form_fields = page.form.fields
    attendees_options = form_fields[field_id][0].__dict__['options']
    return [entry[2] for entry in attendees_options if entry[1]]


def verify_sequential_positions(items: list[AgendaItem]) -> None:
    """Verify that positions are sequential and have no duplicates."""
    positions = [item.position for item in items]
    # Check if positions are sequential from 0 to len(items)-1
    expected = set(range(len(items)))
    actual = set(positions)
    assert (
        expected == actual
    ), f'Positions {positions} are not sequential 0-based integers'
    # Check for duplicates
    assert len(positions) == len(
        set(positions)
    ), f'Duplicate positions found in {positions}'
