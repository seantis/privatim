from datetime import datetime
from sedate import utcnow
from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pyramid.authorization import Allow
from pyramid.authorization import Authenticated
from sqlalchemy.orm import object_session
from privatim.models.attached_document import ConsultationDocument
from privatim.orm import Base
from privatim.orm.meta import UUIDStrPK, UUIDStr

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from privatim.types import ACL


class Status(Base):
    __tablename__ = 'status'
    id: Mapped[UUIDStrPK]
    name: Mapped[Text] = mapped_column(Text, nullable=False)
    consultations = relationship(
        'Consultation', back_populates='status'
    )


class Consultation(Base):
    """Vernehmlassung (Verfahren der Stellungnahme zu einer öffentlichen
    Frage)"""

    __tablename__ = 'consultations'

    id: Mapped[UUIDStrPK]

    documents: Mapped[list[ConsultationDocument]] = relationship(
        back_populates='consultation',
        cascade="all, delete-orphan"
    )
    title = Column(String, nullable=False)

    description = Column(Text)

    comments = Column(Text)

    recommendation = Column(String)

    status_id: Mapped[UUIDStr] = mapped_column(
        ForeignKey('status.id'), index=True
    )
    status = relationship(
        'Status', back_populates='consultations'
    )

    created: Mapped[datetime] = mapped_column(default=utcnow)

    def get_asset(self, name: str) -> ConsultationDocument | None:
        """
        Returns asset by its name, if present.
        """
        return (
            object_session(self)  # type: ignore
            .query(ConsultationDocument)
            .filter_by(
                product_catalogue=self,
                filename=name
            )
            .one_or_none()
        )

    def __acl__(self) -> list['ACL']:
        return [
            (Allow, Authenticated, ['view']),
        ]
