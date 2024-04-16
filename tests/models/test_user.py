from privatim.models import User


def test_set_password(config, organization):
    session = config.dbsession
    user = User(organization=organization)
    session.add(user)
    session.flush()
    user.set_password('Test123!')
    assert user.password != 'Test123!'
    assert user.check_password('Test123!') is True


def test_check_password(config, organization):
    session = config.dbsession
    user = User(organization=organization)
    session.add(user)
    session.flush()
    assert user.check_password('Test123!') is False
    user.set_password('Test123!')
    assert user.check_password(None) is False
    assert user.check_password('') is False
    assert user.check_password('Test123!') is True


def test_groups_no_organization(config, organization):
    session = config.dbsession
    user = User()
    session.add(user)
    session.flush()
    assert user.groups() == []


def test_groups(config, organization):
    session = config.dbsession
    user = User(organization=organization)
    session.add(user)
    session.flush()
    assert user.groups() == [f'org_{organization.id}']
