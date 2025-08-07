from __future__ import annotations


class MailError(Exception):
    pass


class MailConnectionError(MailError, ConnectionError):
    pass


class InactiveRecipient(MailError):
    pass


class InconsistentChain(Exception):
    pass
