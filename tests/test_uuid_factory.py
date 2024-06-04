from privatim.models import Meeting
import pytest
from privatim.route_factories import create_uuid_factory
from pyramid.testing import DummyRequest
from pyramid.httpexceptions import HTTPNotFound
from test_cache import DummyObject
from tests.shared.utils import create_meeting


def test_create_uuid_factory_valid_uuid(session):
    db = session
    meeting = create_meeting()
    db.add(meeting)
    db.flush()
    db.refresh(meeting)

    request = DummyRequest()
    request.matchdict = {'id': str(meeting.id)}
    route_factory = create_uuid_factory(Meeting)
    result = route_factory(request)

    assert isinstance(result, Meeting)
    assert result.id == meeting.id

    request = DummyRequest()
    request.matchdict = {'id': 'invalid-uuid'}

    with pytest.raises(HTTPNotFound):
        route_factory(request)


def test_create_uuid_factory_missing_uuid(session):
    request = DummyRequest()
    request.matchdict = {}

    route_factory = create_uuid_factory(DummyObject())
    with pytest.raises(HTTPNotFound):
        route_factory(request)


def test_create_uuid_factory_not_found(session):
    # Arrange
    create_meeting()

    request = DummyRequest()
    request.matchdict = {'id': 'a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6'}

    route_factory = create_uuid_factory(Meeting)

    # Act & Assert
    with pytest.raises(HTTPNotFound):
        route_factory(request)
