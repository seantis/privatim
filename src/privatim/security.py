from __future__ import annotations
from typing import TYPE_CHECKING

from sqlalchemy.orm import object_session

from privatim.models import User

if TYPE_CHECKING:
    from pyramid.interfaces import IRequest


def query_user(user_id: str, request: 'IRequest') -> User | None:
    if not user_id or not request:
        return None

    user = getattr(request, '_authenticated_user', None)
    if user and object_session(user):
        if user.id == user_id:
            return user

    user = request.dbsession.get(User, user_id)
    if user and request:
        request._authenticated_user = user
    return user


def authenticated_user(request: 'IRequest') -> User | None:
    user_id = request.authenticated_userid
    return query_user(user_id, request)
