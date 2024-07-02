from datetime import datetime
from datetime import timedelta
from datetime import timezone

from privatim.models import PasswordChangeToken
from privatim.testing import DummyRequest
from privatim.views.password_change import password_change_view


def test_password_change_view(pg_config):
    request = DummyRequest()
    result = password_change_view(request)
    assert 'form' in result

    msg = request.messages.pop()[0]
    assert 'Password must have minimal length of 8' in msg['message']


def test_password_change_view_password_strength(config, user):
    config.add_route('password_retrieval', '/password_retrieval')
    session = config.dbsession

    user.email = 'buck@seantis.ch'
    token_obj = PasswordChangeToken(user, '127.0.0.1')
    session.add(token_obj)
    session.flush()

    request = DummyRequest()
    request.client_addr = '127.0.0.1'
    request.params['token'] = token_obj.token
    result = password_change_view(request)
    assert result['valid'] is True
    messages = request.messages.pop()
    assert messages[0]['type'] == 'info'
    assert 'Password must have minimal length' in messages[0]['message']


def test_password_change_view_invalid(pg_config):
    request = DummyRequest()
    request.params['token'] = '1234567'
    request.POST['email'] = 'username'
    request.POST['password'] = ''  # Empty password
    request.POST['password_confirmation'] = ''
    result = password_change_view(request)
    assert 'form' in result
    message = request.messages.pop()[0]
    assert message['type'] == 'danger'
    assert 'There was a problem with your submission.' in message['message']


def test_password_change_view_invalid_confirmation(pg_config):
    request = DummyRequest()
    request.params['token'] = '1234567'
    request.POST['email'] = 'username'
    request.POST['password'] = '12345678'
    request.POST['password_confirmation'] = '12345'
    result = password_change_view(request)
    assert 'form' in result
    message = request.messages.pop()[0]
    assert message['type'] == 'danger'
    assert 'There was a problem with your submission.' in message['message']


def test_password_change_view_invalid_min_length(pg_config):
    request = DummyRequest()
    request.params['token'] = '1234567'
    request.POST['email'] = 'username'
    request.POST['password'] = '123456'
    request.POST['password_confirmation'] = '123456'
    result = password_change_view(request)
    assert 'form' in result
    message = request.messages.pop()[0]
    assert message['type'] == 'danger'
    assert 'There was a problem with your submission.' in message['message']


def test_password_change_view_invalid_username(config, user):
    config.add_route('password_retrieval', '/password_retrieval')
    session = config.dbsession

    user.email = 'buck@seantis.ch'
    token_obj = PasswordChangeToken(user, '127.0.0.1')
    session.add(token_obj)
    session.flush()

    request = DummyRequest()
    request.client_addr = '127.0.0.1'
    request.params['token'] = token_obj.token
    request.POST['email'] = 'username'
    request.POST['password'] = 'Test123!'
    request.POST['password_confirmation'] = 'Test123!'
    result = password_change_view(request)
    messages = request.messages.pop()
    assert messages[0]['type'] == 'danger'
    assert messages[0]['message'] == 'Invalid Request'
    assert 'form' in result


def test_password_change_view_invalid_token(pg_config):
    request = DummyRequest()
    request.params['token'] = '123456'
    request.POST['email'] = 'username'
    request.POST['password'] = 'Ab+12345678'
    request.POST['password_confirmation'] = 'Ab+12345678'
    result = password_change_view(request)
    messages = request.messages.pop()
    assert messages[0]['type'] == 'danger'
    assert messages[0]['message'] == 'Invalid Request'
    assert 'form' in result


def test_password_change_view_expired_token(config, user):
    config.add_route('login', '/login')
    config.add_route('password_retrieval', '/password_retrieval')
    session = config.dbsession

    user.email = 'buck@seantis.ch'
    dt = datetime.utcnow() - timedelta(days=30)
    dt = dt.replace(tzinfo=timezone.utc)
    token_obj = PasswordChangeToken(user, '127.0.0.1',
                                    time_requested=dt)
    session.add(token_obj)
    session.flush()

    request = DummyRequest()
    request.client_addr = '127.0.0.1'
    request.params['token'] = token_obj.token
    result = password_change_view(request)
    assert result['valid'] is False
    messages = request.messages.pop()
    message = messages[0]
    assert message['type'] == 'danger'
    text = message['message']
    assert 'This password reset link has expired.' in text


def test_password_change_view_consumed_token(config, user):
    config.add_route('login', '/login')
    config.add_route('password_retrieval', '/password_retrieval')
    session = config.dbsession

    user.email = 'buck@seantis.ch'
    token_obj = PasswordChangeToken(user, '127.0.0.1')
    session.add(token_obj)
    token_obj.consume('buck@seantis.ch')
    session.flush()

    request = DummyRequest()
    request.client_addr = '127.0.0.1'
    request.params['token'] = token_obj.token
    result = password_change_view(request)
    assert result['valid'] is False
    messages = request.messages.pop()
    message = messages[0]
    assert message['type'] == 'danger'
    text = message['message']
    assert 'This password reset link has expired.' in text


def test_password_change_view_token(config, user):
    config.add_route('login', '/login')
    session = config.dbsession

    user.email = 'buck@seantis.ch'
    token_obj = PasswordChangeToken(user, '127.0.0.1')
    session.add(token_obj)
    session.flush()

    # First attempt fails because of weak password
    request = DummyRequest()
    request.client_addr = '127.0.0.1'
    request.params['token'] = token_obj.token
    request.POST['email'] = 'buck@seantis.ch'
    request.POST['password'] = 'test'
    request.POST['password_confirmation'] = 'test'
    result = password_change_view(request)
    assert 'form' in result

    # Second attempt succeeds
    request.POST['password'] = 'Ab+12345678'
    request.POST['password_confirmation'] = 'Ab+12345678'
    result = password_change_view(request)
    assert result.status_int == 302
    assert result.headers['Location'] == 'http://example.com/login'
