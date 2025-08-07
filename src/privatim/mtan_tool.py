from __future__ import annotations
import hashlib
import secrets

from sqlalchemy import select

from privatim.models import TAN


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from privatim.models import User


class MTanException(Exception):
    pass


class MTanNotFound(MTanException):
    pass


class MTanExpired(MTanException):
    pass


class MTanTool:

    def __init__(self, session: 'Session'):
        self.session = session

    def hash(self, tan: str) -> str:
        tan_b = tan.encode('utf-8')
        return hashlib.sha224(tan_b).hexdigest()

    def tan(self, user_id: str, hashed_tan: str) -> TAN | None:
        if not (user_id and hashed_tan):
            return None

        stmt = (
            select(TAN)
            .filter(TAN.tan == hashed_tan)
            .filter(TAN.user_id == user_id)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def create_tan(
        self,
        user: 'User',
        ip_address: str,
        length: int = 6
    ) -> str:

        chars = 'ABCDEFGHIJKLMNPQRSTUVWXYZ123456789'
        token = ''.join(secrets.choice(chars) for _ in range(length))
        hashed_tan = self.hash(token)

        token_obj = TAN(user, hashed_tan, ip_address)
        self.session.add(token_obj)

        return token

    def verify(self, user_id: str, tan: str) -> 'User':
        hashed_tan = self.hash(tan)
        tan_obj = self.tan(user_id, hashed_tan)
        if not tan_obj:
            raise MTanNotFound(f'TAN "{tan}" not found')
        if tan_obj.expired():
            raise MTanExpired(f'TAN "{tan}" expired')
        return tan_obj.user

    def expire(self, user_id: str, tan: str) -> None:
        hashed_tan = self.hash(tan)
        tan_obj = self.tan(user_id, hashed_tan)
        if not tan_obj:
            raise MTanNotFound(f'TAN "{tan}" not found')
        if tan_obj.expired(hours=None):
            raise MTanExpired(f'TAN "{tan}" already expired')
        tan_obj.expire()
