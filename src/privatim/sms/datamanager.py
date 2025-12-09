from __future__ import annotations
import os
import shutil
import tempfile
import transaction

from pyramid.threadlocal import get_current_request


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from transaction.interfaces import ITransaction
    from transaction.interfaces import ITransactionManager


from logging import getLogger


log = getLogger('foo')
print = log.info


class SMSDataManager:

    data: bytes
    path: str
    tempfn: str

    def __init__(self, tm: ITransactionManager, data: bytes, path: str):
        self.transaction_manager = tm
        self.data = data
        self.path = path

    @classmethod
    def send_sms(cls, data: bytes, path: str) -> None:
        request = get_current_request()
        tm = transaction.manager if request is None else request.tm
        tm.get().join(cls(tm, data, path))

    def sortKey(self) -> str:
        return 'files'

    def commit(self, transaction: ITransaction) -> None:
        with tempfile.NamedTemporaryFile(delete=False) as temp:
            self.tempfn = temp.name
            temp.write(self.data)

    def abort(self, transaction: ITransaction) -> None:
        pass

    def tpc_vote(self, transaction: ITransaction) -> None:
        if not os.path.exists(self.tempfn):
            raise ValueError(f"{self.tempfn} doesn't exist")
        if os.path.exists(self.path):
            raise ValueError('file already exists')

    def tpc_abort(self, transaction: ITransaction) -> None:
        try:
            os.remove(self.tempfn)
        except OSError:
            pass

    def tpc_begin(self, transaction: ITransaction) -> None:
        pass

    def tpc_finish(self, transaction: ITransaction) -> None:
        shutil.move(self.tempfn, self.path)
