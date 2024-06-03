from privatim.models import User, WorkingGroup, Group, GeneralFile
from sqlalchemy import select


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


def test_user_default_profile_picture(session):
    # Create a user without providing a profile_pic_id
    user = User(
        first_name='John',
        last_name='Doe',
        email='john.doe@example.com',
    )
    session.add(user)
    session.flush()

    pic = user.picture
    assert pic.file.saved is True
    assert pic.file.file

    # # Create another user with a custom profile picture
    custom_profile_picture = GeneralFile('custom_profile_pic.jpg',
                                         b'custom_pic_data')
    session.add(custom_profile_picture)
    session.flush()
    session.refresh(custom_profile_picture)

    user_with_custom_pic = User(
        first_name='Jane',
        last_name='Smith',
        email='jane.smith@example.com',
    )
    user_with_custom_pic.profile_pic_id = custom_profile_picture.id
    session.add(user_with_custom_pic)
    session.flush()

    stored_user_with_custom_pic = session.execute(
        select(User).filter_by(email='jane.smith@example.com')
    ).scalar_one_or_none()

    assert (
        stored_user_with_custom_pic.profile_pic.filename
        == 'custom_profile_pic.jpg'
    )
