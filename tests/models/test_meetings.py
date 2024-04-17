from datetime import datetime, timezone
from privatim.models import WorkingGroup, Meeting


def test_working_group_meetings_relationship(config):
    session = config.dbsession
    group = WorkingGroup(name="Working Team")
    session.add(group)
    session.flush()

    group = session.query(WorkingGroup).one()
    assert group.meetings == []

    date = datetime(
        2018,
        10,
        10,
        10,
        10,
        10,
        tzinfo=timezone.utc,
    )
    meeting = Meeting(name="Test Meeting", time=date, attendees=[group])
    session.add_all([group, meeting])
    session.flush()

    group = session.query(WorkingGroup).one()
    session.query(WorkingGroup).one()
    assert group.meetings == [meeting]
