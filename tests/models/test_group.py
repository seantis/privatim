from sqlalchemy import select
from privatim.models import WorkingGroup, User


def test_leading_group(session, user_with_working_group):
    # a group can only have one leader
    # Though a user can lead multiple groups

    user = user_with_working_group
    working_group = session.execute(select(WorkingGroup)).unique().scalar_one()
    assert working_group.name == 'Group'
    assert working_group in user.groups

    # add a leader
    working_group.leader = user
    session.add_all([user, working_group])
    session.flush()

    assert user.leading_groups == [working_group]
    assert working_group.leader == user
    # todo: test making leader of group which user is not part of


def test_leader_nullable(session):

    user = User(
        email='admin@example.org',
        first_name='John',
        last_name='Doe',
        groups=[WorkingGroup(name='Group')],
    )

    session.add_all([user])
    session.flush()
    working_group = session.execute(select(WorkingGroup)).unique().scalar_one()
    assert working_group.leader is None
    working_group.leader = user

    session.add_all([user, working_group])
    session.flush()
    assert user.leading_groups == [working_group]
    assert working_group.leader == user

    # Test that leader is nullable
    new_working_group = WorkingGroup(name="New Group")
    session.add(new_working_group)
    session.flush()
