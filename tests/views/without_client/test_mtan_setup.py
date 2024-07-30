from webob.multidict import MultiDict

from privatim.testing import DummyRequest
from privatim.views.mtan import mtan_setup_view


def test_mtan_setup_view(pg_config, user, mtan_tool, sms_gateway):
    pg_config.add_route('home', '/')
    pg_config.add_route('login', '/login')
    pg_config.add_route('mtan_setup', '/mtan-setup')

    request = DummyRequest()
    response = mtan_setup_view(request)
    assert response.status_int == 302
    assert response.location == 'http://example.com/login'

    request.session['mtan_setup_user'] = user.id
    result = mtan_setup_view(request)
    assert 'form' in result

    request.POST['mobile_number'] = '078 123 45 67'
    result = mtan_setup_view(request)
    assert 'form' in result

    message = sms_gateway.messages[0]
    assert message.receiver == '+41781234567'
    assert 'Privatim Login Token:\n' in message.content
    assert message.sender == 'Privatim'
    tan = message.content.split()[-1]
    request.POST['mtan'] = tan
    response = mtan_setup_view(request)
    assert response.status_int == 302
    assert response.location == 'http://example.com/'
    assert user.mobile_number == '+41781234567'


def test_mtan_setup_view_retry(pg_config, user, mtan_tool, sms_gateway):
    pg_config.add_route('home', '/')
    pg_config.add_route('login', '/login')
    pg_config.add_route('mtan_setup', '/mtan_setup')
    # DummyRequest merges GET and POST data
    request = DummyRequest(post=MultiDict())
    request.session['mtan_setup_user'] = user.id
    request.GET['different_number'] = 'True'
    result = mtan_setup_view(request)
    assert 'form' in result
    assert result['form'].mobile_number.data is None

    request.session['mtan_mobile_number'] = '+41790000001'
    result = mtan_setup_view(request)
    assert 'form' in result
    assert result['form'].mobile_number.data == '+41790000001'

    request.POST['mobile_number'] = '078 111 22 33'
    result = mtan_setup_view(request)
    assert 'form' in result

    message = sms_gateway.messages[0]
    assert message.receiver == '+41781112233'
    assert 'Privatim Login Token:\n' in message.content
    assert message.sender == 'Privatim'
    tan = message.content.split()[-1]
    request.POST['mtan'] = tan
    response = mtan_setup_view(request)
    assert response.status_int == 302
    assert response.location == 'http://example.com/'
    assert user.mobile_number == '+41781112233'
