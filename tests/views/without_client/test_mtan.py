import pytest

from uuid import uuid4

from privatim.mtan_tool import MTanExpired
from privatim.testing import DummyRequest
from privatim.views.mtan import mtan_view


def test_mtan_view(user):
    request = DummyRequest()
    request.session['mtan_user'] = user.id
    data = mtan_view(request)
    assert 'form' in data
    assert hasattr(data['form'], 'mtan')


def test_mtan_view_not_in_session(pg_config):
    pg_config.add_route('login', '/login')
    request = DummyRequest()
    response = mtan_view(request)
    assert response.status_int == 302
    assert response.headers['Location'] == 'http://example.com/login'


def test_mtan_view_submit(pg_config, mtan_tool, user):
    pg_config.add_route('login', '/')
    pg_config.add_route('home', '/')
    tan = mtan_tool.create_tan(user, '127.0.0.1')
    request = DummyRequest()
    request.remote_addr = '127.0.0.2'
    request.session['mtan_user'] = user.id
    request.POST['mtan'] = tan
    response = mtan_view(request)
    assert response.status_int == 302
    assert response.headers['Location'] == 'http://example.com/'
    assert 'mtan_user' not in request.session
    with pytest.raises(MTanExpired):
        mtan_tool.verify(user.id, tan)
    assert user.last_login is not None


def test_mtan_view_submit_case_insensitive(pg_config, mtan_tool, user):
    pg_config.add_route('home', '/')
    tan = mtan_tool.create_tan(user, '127.0.0.1')
    request = DummyRequest()
    request.remote_addr = '127.0.0.2'
    request.session['mtan_user'] = user.id
    request.POST['mtan'] = tan.lower()
    response = mtan_view(request)
    assert response.status_int == 302
    assert response.headers['Location'] == 'http://example.com/'


def test_mtan_view_submit_invalid_tan(mtan_tool, user, caplog):
    request = DummyRequest()
    request.remote_addr = '127.0.0.2'
    request.session['mtan_user'] = user.id
    request.POST['mtan'] = 'test'
    data = mtan_view(request)
    assert 'form' in data
    assert request.session['mtan_user'] == user.id
    # TODO: Reactivate when logging failures
    # msg = '[127.0.0.2] authentication failed: TAN "TEST" not found\n'
    # assert msg in caplog.text


def test_mtan_view_invalid_session(mtan_tool, user, caplog):
    tan = mtan_tool.create_tan(user, '127.0.0.1')
    assert mtan_tool.verify(user.id, tan) == user
    request = DummyRequest()
    request.remote_addr = '127.0.0.3'
    request.session['mtan_user'] = str(uuid4())
    request.POST['mtan'] = tan
    data = mtan_view(request)
    assert 'form' in data
    # TODO: Reactivate when logging failures
    # msg = f'[127.0.0.3] authentication failed: TAN "{tan}" not found\n'
    # assert msg in caplog.text


def test_mtan_view_expired(mtan_tool, user, caplog):
    tan = mtan_tool.create_tan(user, '127.0.0.1')
    tan_obj = mtan_tool.tan(user.id, mtan_tool.hash(tan))
    tan_obj.expire()

    request = DummyRequest()
    request.remote_addr = '127.0.0.3'
    request.session['mtan_user'] = user.id
    request.POST['mtan'] = tan
    data = mtan_view(request)
    assert 'form' in data
    # TODO: Reactivate when logging failures
    # msg = f'[127.0.0.3] authentication failed: TAN "{tan}" expired\n'
    # assert msg in caplog.text
