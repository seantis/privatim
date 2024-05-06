from privatim.testing import DummyRequest
from privatim.views import logout_view


def test_logout_view(config):
    config.add_route('login', '/login')

    request = DummyRequest()
    response = logout_view(request)
    assert response.status_int == 302
    assert response.location == 'http://example.com/login'
