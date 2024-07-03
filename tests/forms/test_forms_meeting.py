from datetime import datetime, timezone
import pytest
from sqlalchemy import select
from privatim.forms.meeting_form import MeetingForm
from privatim.models import User
from privatim.testing import DummyRequest
from tests.shared.utils import create_meeting
from werkzeug.datastructures import MultiDict


class DummyPostData(dict):
    def getlist(self, key):
        v = self[key]
        if not isinstance(v, (list, tuple)):
            v = [v]
        return v


@pytest.mark.skip()
def test_meeting_form_time_not_optional(pg_config):
    meeting = create_meeting()
    session = pg_config.dbsession
    session.add(meeting)
    session.flush()
    # get the user id
    user_id = pg_config.dbsession.execute(
        select(User.id).where(User.email == 'john@doe.org')
    ).scalar_one()

    request = DummyRequest(
        post=MultiDict({'name': 'Team Meeting', 'attendees': [user_id]})
    )
    form = MeetingForm(context=meeting, request=request)

    # Check if the form is not valid due to the missing 'time' field
    assert not form.validate()
    assert 'time' in form.errors
    assert 'This field is required.' in form.errors['time']

    date_time = datetime(
        2018,
        10,
        10,
        10,
        10,
        tzinfo=timezone.utc,
    )
    request = DummyRequest(post=MultiDict(
            {
                'name': 'Team Meeting',
                'time': date_time,
                'attendees': [user_id],
            }
        )
    )
    form = MeetingForm(context=meeting, request=request)
    form.process(DummyPostData({
                'name': 'Team Meeting',
                'time': date_time,
                'attendees': [user_id],
    }))
    assert form.validate()
