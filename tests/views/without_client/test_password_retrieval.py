import logging

from privatim.testing import DummyRequest
from privatim.views.password_retrieval import password_retrieval_view


def test_view(config):
    request = DummyRequest()
    result = password_retrieval_view(request)
    assert 'form' in result.keys()


def test_view_submit(config, user, mailer, caplog):
    caplog.set_level(logging.INFO)
    config.add_route('login', '/login')
    config.add_route('password_change', '/password_change')
    session = config.dbsession

    user.email = 'gregory@house.com'
    session.flush()

    request = DummyRequest()
    request.POST['email'] = 'gregory@house.com'
    request.POST['submit'] = '1'
    result = password_retrieval_view(request)
    assert result.status_int == 302
    assert result.headers['Location'] == 'http://example.com/login'

    # Status message
    messages = request.messages.pop()
    assert 'An email has been sent' in messages[0]['message']

    # Mail
    assert len(mailer.mails) == 1
    message = mailer.mails[0]
    assert message['receivers'].display_name == 'gregory@house.com'
    assert message['receivers'].addr_spec == 'gregory@house.com'

    # Log entry
    msg = 'Password retrieval mail sent to "gregory@house.com"\n'
    assert msg in caplog.text


def test_view_submit_username(config, user, mailer):
    config.add_route('login', '/login')
    config.add_route('password_change', '/password_change')
    session = config.dbsession

    user.first_name = 'Gregory'
    user.last_name = 'House'
    user.email = 'gregory@house.com'
    session.flush()

    request = DummyRequest()
    request.POST['email'] = 'gregory@house.com'
    request.POST['submit'] = '1'
    result = password_retrieval_view(request)
    assert result.status_int == 302

    # Mail
    assert len(mailer.mails) == 1
    message = mailer.mails[0]
    assert message['receivers'].display_name == 'Gregory House'
    assert message['receivers'].addr_spec == 'gregory@house.com'


def test_view_submit_invalid(config):
    request = DummyRequest()
    request.POST['email'] = ''  # Empty username
    request.POST['submit'] = '1'
    result = password_retrieval_view(request)
    assert 'form' in result.keys()


def test_view_submit_invalid_username(config, caplog):
    config.add_route('login', '/login')
    request = DummyRequest()
    request.POST['email'] = 'gregory@house.com'
    request.POST['submit'] = '1'
    result = password_retrieval_view(request)
    assert result.status_int == 302
    assert result.headers['Location'] == 'http://example.com/login'

    # Success message ...
    messages = request.messages.pop()
    assert 'An email has been sent' in messages[0]['message']

    # Log entry
    msg = '[127.0.0.1] password retrieval: User "gregory@house.com" not found'
    assert msg in caplog.text
