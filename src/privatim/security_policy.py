from __future__ import annotations
from datetime import datetime
from typing import Any, TYPE_CHECKING

from pyramid.authorization import ACLAllowed
from pyramid.authorization import ACLDenied
from pyramid.authorization import Allow
from pyramid.authorization import Authenticated
from pyramid.authorization import DENY_ALL
from pyramid.interfaces import ISecurityPolicy
from pyramid.util import is_nonstr_iter
from zope.interface import implementer

from privatim.cache import request_cache
from privatim.security import query_user

if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from pyramid.security import ACLPermitsResult
    from typing import TypeAlias

    from privatim.models import User

    from privatim.types import ACL

    HTTPHeader: TypeAlias = tuple[str, str]


class PasswordException(Exception):
    pass


@implementer(ISecurityPolicy)
class SessionSecurityPolicy:

    timeout:     int | None
    userid_key:  str
    timeout_key: str

    def __init__(
        self,
        prefix:  str = 'auth.',
        timeout: int | None = None
    ) -> None:

        self.userid_key = f'{prefix}userid'
        self.timeout_key = f'{prefix}timeout'
        if timeout:
            timeout = int(timeout)
        self.timeout = timeout

    @request_cache()
    def acl(self, context: Any, request: IRequest) -> list[ACL]:
        if not hasattr(context, '__acl__'):
            return [DENY_ALL]
        if not (acls := list(context.__acl__())):
            return [DENY_ALL]
        return acls

    def reissue(self, request: 'IRequest') -> None:
        if hasattr(request.session, 'regenerate_id'):
            request.session.regenerate_id()

    @request_cache()
    def principals(self, request: 'IRequest') -> list[str]:
        user = self.identity(request)
        if user:
            principals = [Authenticated, f'user:{user.id}']
            return principals
        return []

    def authenticated_userid(self, request: 'IRequest') -> str | None:
        last_accessed = getattr(request.session, 'last_accessed', None)
        timeout = request.session.get(self.timeout_key, None)
        if timeout and last_accessed:
            last_accessed = datetime.fromtimestamp(last_accessed)
            if (datetime.now() - last_accessed).total_seconds() > timeout:
                self.forget(request)
                return None
        return request.session.get(self.userid_key)

    def remember(
        self,
        request:  'IRequest',
        userid:   str,
        **kwargs: Any
    ) -> list['HTTPHeader']:

        self.reissue(request)
        timeout = kwargs.get('max_age', self.timeout)
        if timeout:
            request.session[self.timeout_key] = int(timeout)
        request.session[self.userid_key] = userid
        return []

    def forget(self, request: 'IRequest', **kwargs: Any) -> list['HTTPHeader']:
        self.reissue(request)
        if self.timeout_key in request.session:
            del request.session[self.timeout_key]
        if self.userid_key in request.session:
            del request.session[self.userid_key]
        return []

    def identity(self, request: 'IRequest') -> 'User | None':
        user_id = self.authenticated_userid(request)
        if user_id is None:
            return None
        return query_user(user_id, request)

    def permits(
        self,
        request:    'IRequest',
        context:    Any,
        permission: str
    ) -> 'ACLPermitsResult':

        acl = self.acl(context, request)
        principals = self.principals(request)
        for ace in acl:
            ace_action, ace_principal, ace_permissions = ace
            if ace_principal in principals:
                assert is_nonstr_iter(ace_permissions)
                if permission in ace_permissions:
                    if ace_action == Allow:
                        return ACLAllowed(
                            ace, acl, permission, principals, context
                        )
                    else:
                        return ACLDenied(
                            ace, acl, permission, principals, context
                        )

        return ACLDenied(
            '<default deny>', acl, permission, principals, context
        )
