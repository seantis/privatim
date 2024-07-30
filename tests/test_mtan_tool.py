import pytest

from privatim.mtan_tool import MTanExpired
from privatim.mtan_tool import MTanNotFound
from privatim.mtan_tool import MTanTool


def test_hash(session):
    tool = MTanTool(session)
    hashed = tool.hash('1234ZTA')
    assert tool.hash('1234ZTA') == hashed


def test_tan(session, user):
    tool = MTanTool(session)
    assert tool.tan(user.id, '') is None
    assert tool.tan(user.id, '1234ZTA') is None

    tan = tool.create_tan(user, '127.0.0.1')
    hashed = tool.hash(tan)
    tan_obj = tool.tan(user.id, hashed)
    assert tan_obj.user == user
    assert tan_obj.ip_address == '127.0.0.1'
    assert tan_obj.expired() is False


def test_create_tan(session, user):
    tool = MTanTool(session)
    tan = tool.create_tan(user, '127.0.0.1')
    assert len(tan) == 6
    assert tool.verify(user.id, tan) == user

    tan = tool.create_tan(user, '127.0.0.1', length=5)
    assert len(tan) == 5
    assert tool.verify(user.id, tan) == user


def test_verify(session, user):
    tool = MTanTool(session)
    with pytest.raises(MTanNotFound):
        tool.verify(user.id, '')
    with pytest.raises(MTanNotFound):
        tool.verify(user.id, '1234ZTA')

    tan = tool.create_tan(user, '127.0.0.1')
    assert tool.verify(user.id, tan) == user

    tool.expire(user.id, tan)
    with pytest.raises(MTanExpired):
        tool.verify(user.id, tan)


def test_expire(session, user):
    tool = MTanTool(session)
    with pytest.raises(MTanNotFound) as e:
        tool.expire(user.id, 'test')
    assert 'TAN "test" not found' in str(e)

    tan = tool.create_tan(user, '127.0.0.1')
    tool.expire(user.id, tan)
    with pytest.raises(MTanExpired) as e:
        tool.verify(user.id, tan)

    with pytest.raises(MTanExpired) as e:
        tool.expire(user.id, tan)
    assert f'TAN "{tan}" already expired' in str(e)
