from __future__ import annotations
import enum


from typing import TypedDict
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..types import JSONObject
    from collections.abc import Sequence
    from email.headerregistry import Address


class MailState(enum.IntEnum):
    not_queued = 0
    queued = 10
    temporary_failure = 15
    failed = 20
    inactive_recipient = 30
    bounced = 40
    submitted = 50
    delivered = 60
    read = 70


class _BaseMailAttachment(TypedDict):
    filename:     str
    content:      bytes
    content_type: str


class MailAttachment(_BaseMailAttachment, total=False):
    content_id: str


class RequiredMailParams(TypedDict):
    receivers: Address | Sequence[Address]
    subject:   str
    content:   str


class OptionalMailParams(TypedDict, total=False):
    sender:      Address
    tag:         str
    attachments: list[MailAttachment]


class MailParams(RequiredMailParams, OptionalMailParams):
    pass


class RequiredTemplateMailParams(TypedDict):
    receivers: Address | Sequence[Address]
    template:  str
    data:      JSONObject


class OptionalTemplateMailParams(TypedDict, total=False):
    sender:      Address
    subject:     str
    tag:         str
    attachments: list[MailAttachment]


class TemplateMailParams(
    RequiredTemplateMailParams,
    OptionalTemplateMailParams
):
    pass
