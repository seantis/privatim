from pyramid.httpexceptions import HTTPFound
from pyramid.security import forget


def logout_view(request):
    headers = forget(request)
    url = request.route_url('login')
    return HTTPFound(location=url, headers=headers)
