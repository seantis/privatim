from __future__ import annotations
from zope.interface import Interface
from typing import Any


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from email.headerregistry import Address

    from collections.abc import Sequence
    from ..types import JSONObject
    from .types import MailParams
    from .types import MailState
    from .types import TemplateMailParams
    MailID = Any


class IMailer(Interface):  # pragma: no cover

    # NOTE: We would like to say that kwargs is OptionalMailParams
    #       however there is no way in mypy to express that yet.
    def send(sender:    Address | None,
             receivers: Address | Sequence[Address],
             subject:   str,
             content:   str,
             **kwargs:  Any) -> MailID:
        """
        Send a single email.

        Returns a message uuid.
        """

    def bulk_send(mails: list[MailParams]
                  ) -> list[MailID | MailState]:
        """
        Send multiple emails. "mails" is a list of dicts containing
        the arguments to an individual send call.

        Returns a list of message uuids and their success/failure states
        in the same order as the sending list.
        """

    # NOTE: We would like to say that kwargs is OptionalTemplateMailParams
    #       however there is no way in mypy to express that yet.
    def send_template(sender:    Address | None,
                      receivers: Address | Sequence[Address],
                      template:  str,
                      data:      JSONObject,
                      **kwargs:  Any) -> MailID:
        """
        Send a single email using a template using its id/name.
        "data" contains the template specific data.

        Returns a message uuid.
        """

    def bulk_send_template(mails:            list[TemplateMailParams],
                           default_template: str | None = None,
                           ) -> list[MailID | MailState]:
        """
        Send multiple template emails using the same template.

        Returns a list of message uuids. If a message failed to be sent
        the uuid will be replaced by a MailState value.
        """

    def template_exists(alias: str) -> bool:
        """
        Returns whether a template by the given alias exists.
        """
