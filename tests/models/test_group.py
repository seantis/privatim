from sqlalchemy import select
from privatim.models import WorkingGroup


def test_leading_group(session, user_with_working_group):
    # a group can only have one leader
    # Though a user can lead multiple groups

    user = user_with_working_group
    working_group = session.execute(select(WorkingGroup)).unique().scalar_one()
    assert working_group.name == 'Group'
    assert working_group in user.groups

    # add a leader
    working_group.leader = user
    session.add(working_group)
    session.add(user)
    session.flush()
    session.refresh(user)
    session.refresh(working_group)

    assert user.leading_groups == [working_group]
    assert working_group.leader == user
    # todo: test making leader of group which user is not part of
