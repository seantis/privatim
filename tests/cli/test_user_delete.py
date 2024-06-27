from datetime import datetime
from sqlalchemy import select
from privatim.layouts.layout import DEFAULT_TIMEZONE
from privatim.models import (User, WorkingGroup, Group, Meeting, Consultation)
from privatim.cli.user import _delete_user
from privatim.models.comment import Comment


def test_delete_user_with_relationships(session):
    # Setup: Create a user with various relationships
    user = User(email='test@example.com', first_name='Test', last_name='User')
    session.add(user)
    session.flush()

    # Create a working group with the user as leader
    working_group = WorkingGroup(name='Test Group', leader=user)
    session.add(working_group)

    # Add user to a regular group
    group = Group(name='Regular Group')
    group.users.append(user)
    session.add(group)

    # Create a meeting with the user as an attendee
    meeting = Meeting(
        name='Test Meeting',
        working_group=working_group,
        time=datetime.now(tz=DEFAULT_TIMEZONE),
        attendees=working_group.users,
    )
    meeting.attendees.append(user)
    session.add(meeting)

    # Create a comment by the user
    comment = Comment(content='Test Comment', user=user)
    session.add(comment)
    session.flush()
    session.refresh(comment)
    comment_id = comment.id

    # Create a consultation by the user
    consultation = Consultation(
        title='Test Consultation',
        description='foo',
        recommendation='bar',
        creator=user,
    )
    session.add(consultation)
    session.flush()

    assert _delete_user(session, user.email) is True

    # Verify that the user has been deleted
    deleted_user = session.execute(
        select(User).filter_by(email='test@example.com')
    ).scalar_one_or_none()
    assert deleted_user is None

    # Check if the working group still exists
    updated_working_group = session.get(WorkingGroup, working_group.id)
    if updated_working_group:
        assert updated_working_group.leader is None
        assert updated_working_group.leader_id is None

    # Check if the group still exists
    updated_group = session.get(Group, group.id)
    if updated_group:
        assert user not in updated_group.users

    # Check if the meeting still exists
    updated_meeting = session.get(Meeting, meeting.id)
    if updated_meeting:
        assert user not in updated_meeting.attendees

    # For now we don't want associated comments to be deleted
    deleted_comment = session.get(Comment, comment_id)
    assert deleted_comment is not None

    # Check if the consultation still exists
    updated_consultation = session.get(Consultation, consultation.id)
    assert updated_consultation is not None
    assert updated_consultation.creator is None
