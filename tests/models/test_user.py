from privatim.models import User, WorkingGroup, Group


def test_set_password(config):
    session = config.dbsession

    user = User(email='admin@example.org')
    session.add(user)
    session.flush()
    user.set_password('Test123!')
    assert user.password != 'Test123!'
    assert user.check_password('Test123!') is True


def test_user_password_failure(config):
    session = config.dbsession
    user = User(email='admin@example.org')
    session.add(user)
    session.flush()
    assert user.check_password('Test123!') is False  # No password set yet
    user.set_password('Test123!')
    assert user.check_password('wrongpassword') is False
    assert user.check_password('Test123!') is True


def test_user_groups_empty(config):
    session = config.dbsession
    user = User(email='admin@example.org')
    session.add(user)
    session.flush()
    assert user.groups == []  # No groups associated initially


def test_user_groups_association(config):
    session = config.dbsession
    user = User(email='admin@example.org')
    group = Group(name='Test Group')

    user.groups.append(group)
    session.add_all([user, group])
    session.flush()

    assert group.users == [user]
    assert user.groups == [group]


def test_user_leading_group_relationship(config):
    session = config.dbsession
    user = User(email='admin@example.org')
    group = WorkingGroup(name='Leadership Group')

    group.leader = user

    session.add_all([user, group])
    session.flush()

    group = session.query(Group).filter_by(name='Leadership Group').one()
    user = session.query(User).filter_by(email='admin@example.org').one()

    assert user.leading_groups[0].name == 'Leadership Group'
    assert group.leader.email == 'admin@example.org'


def test_group_type_polymorphism(config):
    session = config.dbsession
    group = Group(name='General Group')
    working_group = WorkingGroup(name='Specific Working Group')
    session.add(group)
    session.add(working_group)
    session.flush()
    assert isinstance(group, Group)
    assert not isinstance(group, WorkingGroup)
    assert isinstance(working_group, WorkingGroup)
    assert isinstance(working_group, Group)  # Inherits from Group
